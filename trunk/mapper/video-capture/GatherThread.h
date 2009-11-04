#ifndef _GATHERTHREAD_H_
#define _GATHERTHREAD_H_

#include "PluginInternals.h"

class GatherThread: public PThread {
public:
	GatherThread(RecordingParameters cp);

	virtual ~GatherThread();

	/**
	 * Returns a frame on top of the frame stack. Returns null
	 * if there is none.
	**/
	AVFrame *getFrame();

	/**
	 * Return true, if the thread is running without errors.
	**/
	bool isAlive();

	/**
	 * Returns recording parameters whith which the recording
	 * was started.
	**/
	const RecordingParameters& getRecordingParameters();

	/**
	 * Returns ffmpeg video stream of the camera being recorded.
	**/
	AVStream *getVideoStream();

	/**
	 * Returns identifier of the camera being recorded (e.g. "/dev/video0")
	**/
	const QString& getDeviceName();

	/**
	 * After returning from this call, the class and video gathering
	 * is fully initialized (i.e. it's safe to use getVideoStream() etc.)
	 * @returns true if successful; false if the class is being destroyed.
	**/
	bool ensureFullyInitialized();

	/**
	 * Returns the count of frames between start of recording and the
	 * first frame that was read from camera.
	**/
	int getInitialBlankFramesCount();

	/**
	 * Reinitializes the recording state without resetting the
	 * camera device. Good e.g. when changing from preview to recording.
	**/
	void restartCounters();
private:
	virtual void doRun();

	void enqueueFrame(AVFrame *frame);

	bool openVideo();

	void closeVideo();

	AVFrame *readFrame();

	enum WhatIsOpened {
		NOTHING,
		FILE,
		CODEC,
		EXIT
	};
	WhatIsOpened whatIsOpened;

	void setWhatIsOpened(WhatIsOpened w);
	
	int getFrameDiffBetweenTimes(timeval time1, timeval time2);

	AVFrame *getFrame_noLock();
private:
	RecordingParameters recordingParameters;

	AVFormatParameters formatParams;
	AVInputFormat *iformat;
	AVFormatContext *pFormatCtx;
	AVCodecContext  *pCodecCtx;
    AVCodec         *pCodec;
	int videoStream;

	pthread_spinlock_t framesLock;
	QList<AVFrame *> frames;

	pthread_spinlock_t initializationLock;
	bool gettingFirstFrame;
	timeval firstFrameTime, recordingStartTime;
	long lastFrameNo;
};

#endif //_GATHERTHREAD_H_
