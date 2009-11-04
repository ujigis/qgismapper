#include "VideoPreviewWidget.h"

VideoPreview::VideoPreview(QWidget *parent, int previewWidth_, int previewHeight_)
	: QWidget(parent)
{
	initializePicture(previewWidth_, previewHeight_);

	setWindowTitle(tr("Video preview"));
	setMinimumWidth(previewWidth);
	setMinimumHeight(previewHeight);
}

VideoPreview::~VideoPreview()
{
	delete[] previewBuffer;
	av_free(previewRgbFrame);
}

void VideoPreview::initializePicture(int width, int height)
{
	int fmt=PreviewPixelFormat;
	char str[100];

	previewWidth=width;
	previewHeight=height;

	int hdrLen=sprintf(str, "P6\n%d %d\n255\n", width, height);

	//create rgb frame
	previewRgbFrame=avcodec_alloc_frame();

	previewBufferLen=hdrLen+avpicture_get_size(fmt, width, height);
	previewBuffer=new uint8_t[previewBufferLen];

	memset(previewBuffer, 0, previewBufferLen);
	memcpy(previewBuffer, str, hdrLen);
	avpicture_fill((AVPicture*)previewRgbFrame, previewBuffer+hdrLen, fmt, width, height);

	setDataValid(false);
}

void VideoPreview::paintEvent(QPaintEvent *)
{
	QPainter painter(this);
	QImage i = QImage::fromData(previewBuffer,previewBufferLen,"PPM");
	painter.drawImage(QPoint(0,0),i);

	if (!previewDataValid) {
		painter.setPen(QPen(Qt::red));
		painter.drawLine(QLine(0, 0, getWidth(), getHeight()));
		painter.drawLine(QLine(getWidth(), 0, 0, getHeight()));
	}
}
