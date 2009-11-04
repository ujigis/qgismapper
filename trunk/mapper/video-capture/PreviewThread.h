#ifndef _PREVIEWTHREAD_H_
#define _PREVIEWTHREAD_H_

#include "PluginInternals.h"
#include "GatherThread.h"
#include "ProcessThread.h"

class PreviewThread: public ProcessThread {
	Q_OBJECT

public:
	PreviewThread(GatherThread *gatherThread_);

	virtual ~PreviewThread();

	/**
	 * Sets the specified VideoPreview widget to display
	 * processed frames. The interval specifies, how many frames
 	 * are there between two displayings (i.e. each 'interval' frame
	 * is shown).
	**/
	void setPreview(VideoPreview *widget, int interval);

signals:
	/**
	 * Emitted when a new frame is prepared to be displayed.
	**/
	void frameReady();

protected:
	virtual bool initializeRun()  { return true; }
	virtual void terminateRun() { }
	virtual void processFrame(AVFrame *picture) { processPreview(picture); }

private:
	void initializePreviewConvertor();
	void uninitializePreviewConvertor();
	void unsetPreviewWidget();
	void processPreview(AVFrame *picture);

private:
	pthread_spinlock_t previewLock;
	VideoPreview *previewWidget;
	int previewInterval;
	int previewCurFrame;
	SwsContext *previewConvertContext;
	bool gettingFirstFrame;
};

#endif //_PREVIEWTHREAD_H_
