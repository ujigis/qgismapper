#include "GatherThread.h"

GatherThread::GatherThread(RecordingParameters cp):
	recordingParameters(cp)
{
	pthread_spin_init(&framesLock, 0);
	pthread_spin_init(&initializationLock, 0);
	whatIsOpened=NOTHING;
	videoStream=-1;
	pCodecCtx=0;
	pFormatCtx=0;
}



GatherThread::~GatherThread()
{
	AVFrame *f;

	while ((f=getFrame())) {
		freePicture(f);
	}

	pthread_spin_destroy(&framesLock);
	pthread_spin_destroy(&initializationLock);
}

AVFrame *GatherThread::getFrame()
{
	pthread_spin_lock(&framesLock);
	AVFrame *rv=getFrame_noLock();
	pthread_spin_unlock(&framesLock);

	return rv;
}


AVFrame *GatherThread::getFrame_noLock()
{
	AVFrame *rv=0;

	if (!frames.empty()) {
		rv=frames.front();
		frames.pop_front();
	}

	return rv;
}



bool GatherThread::isAlive()
{
	pthread_spin_lock(&initializationLock);
	bool rv=(whatIsOpened!=EXIT);
	pthread_spin_unlock(&initializationLock);

	return rv;
}



const RecordingParameters& GatherThread::getRecordingParameters()
{
	return recordingParameters;
}



AVStream *GatherThread::getVideoStream()
{
	if (videoStream==-1) //video stream not initialized (yet)
		return NULL;

	return pFormatCtx->streams[videoStream];
}



const QString& GatherThread::getDeviceName()
{
	return recordingParameters.device;
}



bool GatherThread::ensureFullyInitialized()
{
	pthread_spin_lock(&initializationLock);
	while (whatIsOpened<CODEC) {
		pthread_spin_unlock(&initializationLock);
		usleep(50);
		pthread_spin_lock(&initializationLock);
	}

	bool rv=(whatIsOpened==CODEC);

	pthread_spin_unlock(&initializationLock);

	return rv;
}



void GatherThread::doRun()
{
	AVFrame *frame;
	restartCounters();

	if (!openVideo()) {
		closeVideo();
		setWhatIsOpened(EXIT);
		return;
	}

	while (!shouldStop()) {
		frame=readFrame();
		if (!frame) {
			printf("Error by reading data from camera %s, exiting...\n", recordingParameters.device.toLocal8Bit().data());
			break;
		}

		enqueueFrame(frame);
	}

	setWhatIsOpened(EXIT);

	closeVideo();
}



void GatherThread::enqueueFrame(AVFrame *frame)
{
	pthread_spin_lock(&framesLock);

	timeval curtime;
	gettimeofday(&curtime, 0);
	if (gettingFirstFrame) {
		firstFrameTime=curtime;
		gettingFirstFrame=false;
	}

	//calculate the frame number (or what it should be according to FPS)
	frame->pts=getFrameDiffBetweenTimes(firstFrameTime, curtime);
	
	if (frame->pts==(lastFrameNo+1)) {
		//if the frames are coming too fast, skip the excessive ones
		freePicture(frame);
	} else {
		frames.push_back(frame);
		lastFrameNo=frame->pts;
	}

	pthread_spin_unlock(&framesLock);
}


int GatherThread::getFrameDiffBetweenTimes(timeval time1, timeval time2)
{
	return int((time2-time1)*double(recordingParameters.fps));
}

int GatherThread::getInitialBlankFramesCount()
{
	return getFrameDiffBetweenTimes(recordingStartTime, firstFrameTime);
}

void GatherThread::restartCounters()
{
	pthread_spin_lock(&framesLock);

	AVFrame *f;

	while ((f=getFrame_noLock())) {
		freePicture(f);
	}

	gettingFirstFrame=true;
	gettimeofday(&recordingStartTime, 0);
	lastFrameNo=0;

	pthread_spin_unlock(&framesLock);
}


bool GatherThread::openVideo()
{
	memset((void*)&formatParams, 0, sizeof(formatParams));
#ifdef OLD_FFMPEG
	formatParams.device = recordingParameters.device.toLocal8Bit().data();
	formatParams.channel = 0;
	formatParams.standard = "pal";
#endif
	formatParams.width = recordingParameters.width;
	formatParams.height = recordingParameters.height;
	formatParams.time_base.den = recordingParameters.fps;
	formatParams.time_base.num = 1;
	formatParams.pix_fmt=PIX_FMT_NONE;
	formatParams.prealloced_context=0;
	
	if (!recordingParameters.v4l2)
		iformat = av_find_input_format("video4linux");
	else
		iformat = av_find_input_format("video4linux2");
	
	int err=av_open_input_file(&pFormatCtx, recordingParameters.device.toLocal8Bit().data(), iformat, 0, &formatParams);
	if (err<0) {
		return false;
	}

	if(av_find_stream_info(pFormatCtx)<0)
		return false;

	dump_format(pFormatCtx, 0, recordingParameters.device.toLocal8Bit().data(), false);

	setWhatIsOpened(FILE);

	unsigned int i;
	videoStream=-1;
	for(i=0; i<pFormatCtx->nb_streams; i++) {
		if(pFormatCtx->streams[i]->codec->codec_type==CODEC_TYPE_VIDEO) {
			videoStream=i;
			break;
		}
	}
	if(videoStream==-1)
		return false;

	pCodecCtx=pFormatCtx->streams[videoStream]->codec;

	pCodec=avcodec_find_decoder(pCodecCtx->codec_id);
	if(pCodec==NULL)
		return false;

	if(avcodec_open(pCodecCtx, pCodec)<0)
		return false;

	setWhatIsOpened(CODEC);

	return true;
}



void GatherThread::closeVideo()
{
	pthread_spin_lock(&initializationLock);
	if (whatIsOpened>=CODEC && pCodecCtx)
		avcodec_close(pCodecCtx);
	if (whatIsOpened>=FILE && pFormatCtx)
		av_close_input_file(pFormatCtx);
	pthread_spin_unlock(&initializationLock);
}



AVFrame *GatherThread::readFrame()
{
	AVFrame *pFrame=allocPicture(pFormatCtx->streams[videoStream]->codec->pix_fmt, formatParams.width, formatParams.height);
	AVFrame decFrame;
	int frameFinished;
	AVPacket packet;

	while (av_read_frame(pFormatCtx, &packet)>=0) {
		if(packet.stream_index==videoStream) {
			if (avcodec_decode_video(pCodecCtx, &decFrame, &frameFinished, packet.data, packet.size)<0) {
				av_free_packet(&packet);

				return 0;
			}

			if(frameFinished) {
				av_picture_copy((AVPicture*)pFrame, (AVPicture*)&decFrame, pFormatCtx->streams[videoStream]->codec->pix_fmt, formatParams.width, formatParams.height);
				
				av_free_packet(&packet);
				return pFrame;
			}
		}
		av_free_packet(&packet);
	}

	return 0;
}



void GatherThread::setWhatIsOpened(WhatIsOpened w)
{
	pthread_spin_lock(&initializationLock);
	whatIsOpened=w;
	pthread_spin_unlock(&initializationLock);
}
