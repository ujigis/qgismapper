#ifndef _PLUGINVIDEOWORKER_H_
#define _PLUGINVIDEOWORKER_H_

#include <QtGui>
#include <QList>
#include <QString>
#include <QWidget>
extern "C" {
#include <avformat.h>
#include <swscale.h>
}
#include <pthread.h>

#include "VideoPreviewWidget.h"

/**
 * Recording parameters of a single recording session/thread.
**/
class RecordingParameters {
public:
	RecordingParameters(QString outputFile, QString codec, long bitrateInKBits, QString device, int width, int height, int fps, bool v4l2) {
		this->outputFile=outputFile;
		this->codec=codec;
		this->bitrateInKBits=bitrateInKBits;
		this->device=device;
		this->width=width;
		this->height=height;
		this->fps=fps;
		this->v4l2=v4l2;
	}

	bool isRecordingEquivalentTo(const RecordingParameters &p) const {
		return (this->device==p.device &&
			this->width==p.width &&
			this->height==p.height &&
			this->fps==p.fps &&
			this->v4l2==p.v4l2
		);
	}

public:
	///file the recording will be saved to
	QString outputFile;

	///codec used to encode the video
	QString codec;

	///bitrate of the encoding codec (in KBit/s)
	long bitrateInKBits;

	///device descriptor
	QString device;

	///width of video to be recorded
	int width;
	///height of video to be recorded
	int height;
	///frames per second of video to be recorded
	int fps;

	///use v4l2 driver for recording
	bool v4l2;
};


/**
 * Describes single camera mode.
**/
class CameraMode {
public:
	CameraMode() {} //for swig...
	CameraMode(int w, int h, int fps_): width(w), height(h), fps(fps_) {}
public:
	///image width
	int width;

	///image height
	int height;

	///frames per second (at current resolution)
	int fps;
};


/**
 * Contains informations about available features of a camera device
**/
class CameraCapabilities {
public:
	///list of available camera modes
	QList<CameraMode> modes;

	///Does the device support video4linux 2?
	bool v4l2;
};





/**
 * Initializes required libraries etc.
**/
bool initializeVideo();

/**
 * Uninitializes libraries, frees occupied memory
**/
bool uninitializeVideo();

/**
 * Returns true, if the specified device is available on system; false otherwise
**/
bool isDevicePresent(const QString& device);

/**
 * Returns list of identification strings of recognized camera devices.
**/
QStringList getDevices();

/**
 * Returns capabilities of the specified camera device
**/
CameraCapabilities getDeviceCapabilities(const QString& device);

/**
 * Start recording with specified cameras (and according settings)
**/
bool startRecording(QList<RecordingParameters> cameras);

/**
 * Stop all recording
**/
void stopRecording();

/**
 * Returns true, if recording is active for the device. Returns false if the recording
 * wasn't started, was stopped or was interrupted by error.
**/
bool isDeviceBeingRecorded(const QString& device);

/**
 * Activates recorded image preview output into specified widget. The call
 * is only effective after recording starts.
 * @param source device and it's parameters to be previewed.
 * @param widget widget the preview should be displayed in. NULL if the preview
 * 				 should be turned off.
 * @param framesInterval interval between displaying 2 frames (1 for displaying each one)
**/
void setPreviewForDevice(const RecordingParameters &source, VideoPreview *widget, int framesInterval);


////////////
// PRIVATE STUFF..


/**
 * Generic internal thread class
**/
class PThread : public QThread {
	Q_OBJECT

private:
	enum {THREADSTOP_NO=0, THREADSTOP_YES, THREADSTOP_DONE};

public:
	PThread() {
		pthread_spin_init(&threadLock, 0);
		threadStop=THREADSTOP_NO;
	}
	virtual ~PThread() {
		terminate();
	}

	/**
	 * QThread run() method encapsulating the pthread functionality
	**/
	virtual void run() {
		doRun();
		exiting();
	}

	/**
	 * Tell the thread to quit and wait until it does so.
	**/
	bool stop() {
		pthread_spin_lock(&threadLock);
		if (threadStop==THREADSTOP_DONE) {
			pthread_spin_unlock(&threadLock);
			return false;
		}
	
		threadStop=THREADSTOP_YES;
		pthread_spin_unlock(&threadLock);
	
		wait();

		threadStop=THREADSTOP_DONE;

		return true;
	}

	/**
	 * Return, whether the thread is in running state (i.e. not about to quit or terminated)
	**/
	bool isRunning() {
		pthread_spin_lock(&threadLock);
		bool rv=(threadStop==THREADSTOP_NO);
		pthread_spin_unlock(&threadLock);

		return rv;
	}
protected:
	virtual void doRun() = 0;

	/**
	 * Return, whether the thread should stop.
	**/
	bool shouldStop() {
		pthread_spin_lock(&threadLock);
		bool stop=(bool)threadStop;
		pthread_spin_unlock(&threadLock);

		return stop;
	}

	/**
	 * Mark the thread as exited.
	**/
	void exiting() {
		pthread_spin_lock(&threadLock);
		threadStop=THREADSTOP_DONE;
		pthread_spin_unlock(&threadLock);
	}

private:
	pthread_spinlock_t threadLock;
	int threadStop;
};

#endif
