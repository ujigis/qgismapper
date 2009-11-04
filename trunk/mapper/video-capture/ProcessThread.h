#ifndef _PROCESSTHREAD_H_
#define _PROCESSTHREAD_H_

#include "PluginInternals.h"
#include "GatherThread.h"

/**
 * A generic video processing thread.
**/
class ProcessThread: public PThread {
public:
	ProcessThread(GatherThread *gatherThread_);

	virtual ~ProcessThread();
protected:
	/**
	 * Generic video processing method, that calls methods
	 * initializeRun(), terminateRun() and processFrame(). This
	 * shouldn't be overriden in the derived classes.
	**/
	virtual void doRun();

	/**
	 * Initialize the processing
	**/
	virtual bool initializeRun() =0;

	/**
	 * Uninitialize the processing
	**/
	virtual void terminateRun() =0;

	/**
	 * Process a single frame
	**/
	virtual void processFrame(AVFrame *picture) =0;

protected:
	GatherThread *gatherThread;

private:
	/**
	 * True if doRun() is currently waiting for
	 * first frame. This is used to determine delay
	 * between start of camera initialization and first
	 * received frame.
	**/
	bool gettingFirstFrame;
};

#endif //_PROCESSTHREAD_H_
