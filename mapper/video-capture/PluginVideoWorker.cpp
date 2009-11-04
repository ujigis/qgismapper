//code based on http://www.inb.uni-luebeck.de/~boehme/libavcodec_update.html
//and http://www.cryptosystem.org/archives/2006/03/libavcodec-libavformat-sample-code/


#include <stdio.h>
#include <stdlib.h>
#include <sys/timeb.h>
#include <sys/stat.h>
#include <asm/errno.h>
#include <assert.h>

#include <sys/types.h>
#include <dirent.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <linux/videodev2.h>
#include <linux/videodev.h>

#include "PluginVideoWorker.h"
#include "GatherThread.h"
#include "CompressThread.h"
#include "PreviewThread.h"

#include <QtGui>

#ifndef OLD_FFMPEG
extern "C" {
  #include <avdevice.h>
}
#endif

using namespace std;



AVFrame *allocPicture(int pix_fmt, int width, int height)
{
	AVFrame *picture;
	uint8_t *picture_buf;
	int size;
	
	picture = avcodec_alloc_frame();
	if (!picture)
		return NULL;
	size = avpicture_get_size(pix_fmt, width, height);
	picture_buf = (uint8_t*)av_malloc(size);
	if (!picture_buf) {
		av_free(picture);
		return NULL;
	}
	avpicture_fill((AVPicture *)picture, picture_buf, pix_fmt, width, height);
	//printf("A %x %x\n", picture, picture_buf);
	return picture;
}

void freePicture(AVFrame *f)
{
	//printf("F %x %x\n", f, f->data[0]);
	av_free(f->data[0]);
	av_free(f);
}


int timeval_subtract(timeval *result, timeval *x, timeval *y)
{
	if (x->tv_usec < y->tv_usec) {
		int nsec = (y->tv_usec - x->tv_usec) / 1000000 + 1;
		y->tv_usec -= 1000000 * nsec;
		y->tv_sec += nsec;
	}
	if (x->tv_usec - y->tv_usec > 1000000) {
		int nsec = (x->tv_usec - y->tv_usec) / 1000000;
		y->tv_usec += 1000000 * nsec;
		y->tv_sec -= nsec;
	}
	
	result->tv_sec = x->tv_sec - y->tv_sec;
	result->tv_usec = x->tv_usec - y->tv_usec;
	
	return x->tv_sec < y->tv_sec;
}


double operator-(timeval x, timeval y)
{
	timeval t;
	timeval_subtract(&t, &x, &y);

	return double(t.tv_sec)+double(t.tv_usec)/1000000;
}



////////////////////// GENERIC ///////////////////////////

bool initializeVideo()
{
#ifndef OLD_FFMPEG
	avcodec_register_all();
	avdevice_register_all();
#endif
	av_register_all();

	return true;
}

bool uninitializeVideo()
{
	return true;
}

struct CameraProcess {
public:
	CameraProcess():
		gatherThread(0), processThread(0), previewWidget(0),recording(false)
	{ }
	
public:
	GatherThread *gatherThread;
	ProcessThread *processThread;
	VideoPreview *previewWidget;
	int previewInterval;
	bool recording;
};

QHash<QString, CameraProcess> cameraProcesses;

void stopProcessing(QString device)
{
	if (!cameraProcesses.contains(device))
		return;

	if (cameraProcesses[device].processThread!=0) {
		cameraProcesses[device].processThread->stop();
		delete cameraProcesses[device].processThread;

		cameraProcesses[device].processThread=0;
		cameraProcesses[device].recording=false;
	}
}


void stopGathering(QString device)
{
	if (!cameraProcesses.contains(device))
		return;

	if (cameraProcesses[device].gatherThread!=0) {
		cameraProcesses[device].gatherThread->stop();
		delete cameraProcesses[device].gatherThread;

		cameraProcesses[device].gatherThread=0;
	}
}



void stopRecording()
{
	QHash<QString, CameraProcess>::iterator cameraProcessI;
	QList<QString> devsToRemove;
	QList<QString>::iterator devsI;

	for (cameraProcessI=cameraProcesses.begin(); cameraProcessI!=cameraProcesses.end(); cameraProcessI++) {
		if (cameraProcessI.value().recording) {
			if (cameraProcessI->previewWidget)
				setPreviewForDevice(cameraProcessI->gatherThread->getRecordingParameters(), 0, 1);
			
			stopProcessing(cameraProcessI.key());
			stopGathering(cameraProcessI.key());

			devsToRemove.append(cameraProcessI.key());
		}
	}

	for (devsI=devsToRemove.begin(); devsI!=devsToRemove.end(); devsI++) {
		cameraProcesses.remove(*devsI);
	}
}



void startGathering(const RecordingParameters &source)
{
	if (!cameraProcesses.contains(source.device))
		cameraProcesses[source.device]=CameraProcess();

	if (!cameraProcesses[source.device].gatherThread) {
		cameraProcesses[source.device].gatherThread=new GatherThread(source);
		cameraProcesses[source.device].gatherThread->start();
	} else {
		assert(cameraProcesses[source.device].gatherThread->getRecordingParameters().isRecordingEquivalentTo(source));

		cameraProcesses[source.device].gatherThread->restartCounters();
	}
}


void startRecording(const RecordingParameters& camera)
{
	//ensure the right gatherer is running
	if (!cameraProcesses.contains(camera.device))
		startGathering(camera);
	else if (!cameraProcesses[camera.device].gatherThread->getRecordingParameters().isRecordingEquivalentTo(camera)) {
		stopGathering(camera.device);
		startGathering(camera);
	}

	//start compression
	ProcessThread *processThread=new CompressThread(cameraProcesses[camera.device].gatherThread, camera.outputFile, camera.codec, camera.bitrateInKBits);
	processThread->start();

	cameraProcesses[camera.device].processThread=processThread;
	cameraProcesses[camera.device].recording=true;

	if (cameraProcesses[camera.device].previewWidget) {
		setPreviewForDevice(camera, cameraProcesses[camera.device].previewWidget, cameraProcesses[camera.device].previewInterval);
	}
}



bool startRecording(QList<RecordingParameters> cameras)
{
	try {
		QList<RecordingParameters>::iterator i;

		for (i=cameras.begin(); i!=cameras.end(); i++) {
			stopProcessing(i->device);
			startRecording(*i);
		}
	} catch (...) {
		stopRecording();
		return false;
	}

	return true;
}



bool isDeviceBeingRecorded(const QString& device)
{
	if (!cameraProcesses.contains(device)) return false;

	CameraProcess& cp=cameraProcesses[device];

	return (cp.gatherThread && cp.gatherThread->isRunning()) &&
		(cp.processThread && cp.processThread->isRunning()) &&
		cp.recording;
}



void setPreviewForDevice(const RecordingParameters &source, VideoPreview *widget, int framesInterval)
{
	if (!widget) {
		if (cameraProcesses.contains(source.device)) {
			if (!cameraProcesses[source.device].recording) {
				stopProcessing(source.device);
				stopGathering(source.device);
				cameraProcesses.remove(source.device);
				return;
			} else {
				dynamic_cast<PreviewThread*>(cameraProcesses[source.device].processThread)->setPreview(widget, framesInterval);
			}
		}
	}

	if (!cameraProcesses.contains(source.device))
		startGathering(source);
	else if (!cameraProcesses[source.device].gatherThread->getRecordingParameters().isRecordingEquivalentTo(source)) {
		if (cameraProcesses[source.device].recording)
			throw "Tried to set preview for another format than the current recording session handles...";
		stopProcessing(source.device);

		stopGathering(source.device);
		startGathering(source);
	}
	
	if (!cameraProcesses[source.device].recording) {
		cameraProcesses[source.device].processThread=new PreviewThread(cameraProcesses[source.device].gatherThread);
		cameraProcesses[source.device].processThread->start();
	}

	dynamic_cast<PreviewThread*>(cameraProcesses[source.device].processThread)->setPreview(widget, framesInterval);

	cameraProcesses[source.device].previewWidget=widget;
	cameraProcesses[source.device].previewInterval=framesInterval;
}



bool isDevicePresent(const QString& device)
{
	struct stat st;

	if (stat(device.toLocal8Bit().data(), &st)==0)
		return true;

	return false;
}




QStringList getDevices()
{
	QStringList l=QDir("/dev/", "video*", QDir::Name | QDir::IgnoreCase, QDir::System).entryList();

	QStringList rv;
	QStringList::const_iterator iter;
	for (iter = l.constBegin(); iter != l.constEnd(); iter++) {
		rv<< QString("/dev/")+*iter;
	}

	return rv;
}




int fi2fps(v4l2_fract f) {
	return int(float(f.denominator)/float(f.numerator));
}

v4l2_fract operator /(v4l2_fract f, int v)
{
	f.denominator*=v;
	return f;
}

v4l2_fract operator +(v4l2_fract f1, v4l2_fract f2)
{
	v4l2_fract f;

	f.denominator=f1.denominator*f2.denominator;
	f.numerator=f1.numerator*f2.denominator+f2.numerator*f1.denominator;
	
	return f;
}

v4l2_fract& operator +=(v4l2_fract &f1, v4l2_fract f2)
{
	f1=f1+f2;
	return f1;
}

v4l2_fract operator -(v4l2_fract f1)
{
	f1.numerator=-f1.numerator;
	return f1;
}

v4l2_fract operator -(v4l2_fract f1, v4l2_fract f2)
{
	return f1+(-f2);
}

bool operator <(v4l2_fract f1, v4l2_fract f2)
{
	return (float(f1.numerator)/float(f1.denominator))<(float(f2.numerator)/float(f2.denominator));
}

void getDeviceCapabilities_enumFps(int fd, CameraCapabilities &cp, __u32 pixelformat, __u32 width, __u32 height)
{
	int fpsI;

	v4l2_frmivalenum frameFps;

	frameFps.pixel_format=pixelformat;
	frameFps.width=width;
	frameFps.height=height;

	for (fpsI=0; ; fpsI++) {
		frameFps.index=fpsI;
		if (ioctl(fd, VIDIOC_ENUM_FRAMEINTERVALS, &frameFps))
			break;

		if (frameFps.type==V4L2_FRMIVAL_TYPE_DISCRETE) {
			cp.modes.push_back(CameraMode(width, height, fi2fps(frameFps.discrete)));
		} else {
			v4l2_fract step;

			if (frameFps.type==V4L2_FRMIVAL_TYPE_CONTINUOUS)
				step=(frameFps.stepwise.max-frameFps.stepwise.min)/10;
			else
				step=frameFps.stepwise.step;

			while (frameFps.stepwise.min<frameFps.stepwise.max) {
				cp.modes.push_back(CameraMode(width, height, fi2fps(frameFps.stepwise.min)));

				frameFps.stepwise.min+=step;
			}

			cp.modes.push_back(CameraMode(width, height, fi2fps(frameFps.stepwise.max)));
		}
	}
}

void getDeviceCapabilities_enumFrameSizes(int fd, CameraCapabilities &cp, __u32 pixelformat)
{
	v4l2_frmsizeenum frameSizes;
	int fsizeI;

	frameSizes.pixel_format=pixelformat;

	for (fsizeI=0; ; fsizeI++) {
		frameSizes.index=fsizeI;
		if (ioctl(fd, VIDIOC_ENUM_FRAMESIZES, &frameSizes))
			break;

		if (frameSizes.type==V4L2_FRMSIZE_TYPE_DISCRETE) {
			getDeviceCapabilities_enumFps(fd, cp, pixelformat, frameSizes.discrete.width, frameSizes.discrete.height);
		} else { //continuous, stepwise
			int stepW, stepH;

			if (frameSizes.type==V4L2_FRMSIZE_TYPE_CONTINUOUS) {
				stepW=(frameSizes.stepwise.max_width-frameSizes.stepwise.min_width)/10;
				stepH=(frameSizes.stepwise.max_height-frameSizes.stepwise.min_height)/10;
			} else {
				stepW=frameSizes.stepwise.step_width;
				stepH=frameSizes.stepwise.step_height;
			}

			while (frameSizes.stepwise.min_width<frameSizes.stepwise.max_width) {
				getDeviceCapabilities_enumFps(fd, cp, pixelformat, frameSizes.stepwise.min_width, frameSizes.stepwise.min_height);

				frameSizes.stepwise.min_width+=stepW;
				frameSizes.stepwise.min_height+=stepH;
			}

			getDeviceCapabilities_enumFps(fd, cp, pixelformat, frameSizes.stepwise.max_width, frameSizes.stepwise.max_height);

			break; //there won't by any more mode definitions
		}
	}
}

CameraCapabilities getDeviceCapabilities(const QString& device)
{
	CameraCapabilities cp;

	int fd=open(device.toLocal8Bit().data(), O_RDWR);

	v4l2_capability vc;
	//first try v4l2 interface
	if (ioctl(fd, VIDIOC_QUERYCAP, &vc)!=0) {
		cp.v4l2=false;
		video_capability vc1;
		if (ioctl(fd, VIDIOCGCAP, &vc1)!=0)
			printf("Can't get camera %s caps using either v4l(2)...\n", device.toLocal8Bit().data());
		
		cp.modes.push_back(CameraMode(vc1.maxwidth, vc1.maxheight, 30));
		cp.modes.push_back(CameraMode(vc1.maxwidth, vc1.maxheight, 25));
		cp.modes.push_back(CameraMode(vc1.maxwidth, vc1.maxheight, 15));
		cp.modes.push_back(CameraMode(vc1.minwidth, vc1.minheight, 30));
		cp.modes.push_back(CameraMode(vc1.minwidth, vc1.minheight, 25));
		cp.modes.push_back(CameraMode(vc1.minwidth, vc1.minheight, 15));
	} else {
		cp.v4l2=true;
		/*
		printf("v4l2 device: %d | %s | %s\n", vc.capabilities&V4L2_CAP_VIDEO_CAPTURE, vc.driver, vc.card);
		printf("video formats:\n");
		*/

		int fmtI;

		v4l2_fmtdesc fmtDesc;
		
		for (fmtI=0; ; fmtI++) {
			fmtDesc.index=fmtI;
			fmtDesc.type=V4L2_BUF_TYPE_VIDEO_CAPTURE;
			if (ioctl(fd, VIDIOC_ENUM_FMT, &fmtDesc))
				break;
			
			/*
			printf("\tpixel format: %c%c%c%c%s - %s\n",
				((char*)&fmtDesc.pixelformat)[0], ((char*)&fmtDesc.pixelformat)[1], ((char*)&fmtDesc.pixelformat)[2], ((char*)&fmtDesc.pixelformat)[3],
				(fmtDesc.flags&V4L2_FMT_FLAG_COMPRESSED)?" (compressed)":"", fmtDesc.description
			);
			*/

			if (fmtDesc.flags&V4L2_FMT_FLAG_COMPRESSED) //hopefully there is another format :-)
				continue;

			getDeviceCapabilities_enumFrameSizes(fd, cp, fmtDesc.pixelformat);
		}

		if (cp.modes.size()==0) { //fallback
			v4l2_format fmt;
			fmt.type=V4L2_BUF_TYPE_VIDEO_CAPTURE;
			if (ioctl(fd, VIDIOC_G_FMT, &fmt)==0) {
				//printf("%d %d\n", fmt.fmt.pix.width, fmt.fmt.pix.height);
				cp.modes.push_back(CameraMode(fmt.fmt.pix.width, fmt.fmt.pix.height, 30));
				cp.modes.push_back(CameraMode(fmt.fmt.pix.width, fmt.fmt.pix.height, 25));
				cp.modes.push_back(CameraMode(fmt.fmt.pix.width, fmt.fmt.pix.height, 15));
			}
		}
	}
	close(fd);

	return cp;
}



#ifdef MAKETEST

int main(int argc, char **argv)
{
	QApplication a(argc, argv);

	printf("INIT: %d\n", initializeVideo());

	QString dev=getDevices()[0];
	CameraCapabilities devCap=getDeviceCapabilities(dev);
	CameraMode m=devCap.modes[0];

	RecordingParameters cp("test.avi", "mpeg4", 800, "/dev/video0", m.width, m.height, 15, devCap.v4l2);
	QList<RecordingParameters> cps;
	cps.push_back(cp);

	startRecording(cps);

	VideoPreview vpw;
	vpw.show();
	setPreviewForDevice(cp, &vpw, 5);
	
	a.exec();

	stopRecording();

	printf("DEINIT: %d\n", uninitializeVideo());

	return 0;
}
#endif
