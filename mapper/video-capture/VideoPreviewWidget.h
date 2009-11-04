#ifndef _VIDEOPREVIEWWIDGET_H_
#define _VIDEOPREVIEWWIDGET_H_

#include <QtGui>
#include <QList>
#include <QString>
#include <QWidget>

extern "C" {
#include <avformat.h>
#include <swscale.h>
}

#define PreviewPixelFormat PIX_FMT_RGB24

/**
 * A widget capable of showing images from video recorder
**/
class VideoPreview : public QWidget
{
	Q_OBJECT

public:
	VideoPreview(QWidget *parent = 0, int previewWidth_=150, int previewHeight_=100);
	virtual ~VideoPreview();

	/**
	 * Returns currently-to-be-rendered frame.
	**/
	AVFrame *getFrame() { setDataValid(true); return previewRgbFrame; }

	/**
	 * Returns preview width.
	**/
	const int &getWidth() {return previewWidth;}

	/**
	 * Returns preview height.
	**/
	const int &getHeight() {return previewHeight;}

	/**
	 * Set whether the data is valid (if the data isn't valid, a
	 * red cross is drawn over image to indicate "error").
	**/
	void setDataValid(bool val) { previewDataValid=val; }
public slots:
	void updatePreview() { this->repaint(); }
protected:
	void paintEvent(QPaintEvent *event);

private:
	void initializePicture(int width, int height);

	int previewWidth;
	int previewHeight;

	AVFrame *previewRgbFrame;
	uint8_t *previewBuffer;
	int previewBufferLen;

	bool previewDataValid;
};

#endif
