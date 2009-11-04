#include "PreviewThread.h"

PreviewThread::PreviewThread(GatherThread *gatherThread_):
	ProcessThread(gatherThread_)
{
	pthread_spin_init(&previewLock, 0);
	previewConvertContext=0;
	previewWidget=0;
}



PreviewThread::~PreviewThread()
{
	pthread_spin_destroy(&previewLock);

	unsetPreviewWidget();
	uninitializePreviewConvertor();
}



void PreviewThread::setPreview(VideoPreview *widget, int interval)
{
	pthread_spin_lock(&previewLock);

	unsetPreviewWidget();

	previewWidget=widget;
	previewInterval=interval;
	previewCurFrame=0;
	if (widget) {
		initializePreviewConvertor();

		connect(this, SIGNAL(frameReady()), widget, SLOT(updatePreview()));
	}

	pthread_spin_unlock(&previewLock);
}


void PreviewThread::initializePreviewConvertor()
{
	if (!gatherThread->ensureFullyInitialized())
		return;

	uninitializePreviewConvertor();

	AVCodecContext *sourceCodec=gatherThread->getVideoStream()->codec;

	previewConvertContext=sws_getContext(
		sourceCodec->width, sourceCodec->height, sourceCodec->pix_fmt,
		previewWidget->getWidth(), previewWidget->getHeight(), PreviewPixelFormat,
		SWS_BICUBIC, NULL, NULL, NULL
	);
}



void PreviewThread::uninitializePreviewConvertor()
{
	if (previewConvertContext) {
		sws_freeContext(previewConvertContext);
		previewConvertContext=0;
	}
}



void PreviewThread::unsetPreviewWidget()
{
	if (previewWidget) {
		previewWidget->setDataValid(false);
		emit frameReady(); //redraw the frame (to display nothing)

		//NOTE: for some reason, this kills qgis.. however, after deleting
		//the widget, disconnect is performed automagically, thus
		//we may skip this step (though some unnecessary redrawing might
		//be performed...)
		//disconnect(this, 0, previewWidget, 0);
	}

	previewWidget=0;
}



void PreviewThread::processPreview(AVFrame *picture)
{
	pthread_spin_lock(&previewLock);
	if (previewWidget) {
		if (previewCurFrame==0) {
			sws_scale(previewConvertContext,
				picture->data, picture->linesize, 0, gatherThread->getVideoStream()->codec->height,
				previewWidget->getFrame()->data, previewWidget->getFrame()->linesize
			);

			emit frameReady();
		}

		previewCurFrame++;
		if (previewCurFrame>=previewInterval)
			previewCurFrame=0;
	}
	pthread_spin_unlock(&previewLock);
}
