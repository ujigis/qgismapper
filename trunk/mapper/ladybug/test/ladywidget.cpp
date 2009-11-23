/******************************************************************************
 *   Copyright (c) 2009 Martin Dobias
 *
 *   This program is free software; you can redistribute it and/or modify
 *   it under the terms of the GNU General Public License as published by
 *   the Free Software Foundation; either version 2 of the License, or
 *   (at your option) any later version.
 ******************************************************************************/

#include "ladywidget.h"

#include <QKeyEvent>

LadyWidget::LadyWidget(Ladybug& cam, QString streamName, QWidget* p)
 : QWidget(p), mCam(cam), mStreamName(streamName)
{
  // this is supposed to be direct connection
  connect(&cam, SIGNAL(capturedFrame(LadybugFrame)), this, SLOT(receivedFrame(LadybugFrame)) );

	connect(&mTfps, SIGNAL(timeout()), this, SLOT(updateFps()));
	mTfps.start(1000);
	mFrames=0;
	mFps=0;
	mMBytes = 0;
	mMBps = 0;
	mColor = false;
}
	
void LadyWidget::paintEvent(QPaintEvent * event)
{
	QPainter p(this);

  int x=0;
  for (int i = 0; i < 6; i++)
  {
    if (!mLastFrame.preview[i].isNull())
    {
      p.drawImage(x,0, mLastFrame.preview[i]);
      x += mLastFrame.preview[i].width() + 10;
    }
  }

  if (x == 0) p.drawText(20,100, "NO PREVIEW");
	
	QString txt = QString("%1 fps").arg(mFps);
	p.setPen(Qt::red);
	p.drawText(20,20, txt);
  txt = QString("behind %1").arg(mLastFrame.framesBehind);
	p.drawText(20,40, txt);
	txt = QString("data ") + QString::number(mMBps, 'f', 1) + "MB/s";
	p.drawText(20,60, txt);
  if (mCam.isRecording())
	{
    txt = QString("REC: %1 MB/s, %2 frames, %3 discarded")
            .arg(mLastFrame.megabytesWritten, -1, 'f',1)
            .arg(mLastFrame.framesWritten)
            .arg(mLastFrame.framesDiscarded);
		p.drawText(20,80, txt);
	}

  bool autoControl;
  int jpgQuality, bufferUsage;
  mCam.jpegCompression(autoControl, jpgQuality, bufferUsage);
  p.drawText(20,100, QString("JPG: auto %1 / quality %2 / usage %3").arg(autoControl).arg(jpgQuality).arg(bufferUsage));

  const LadybugCounter& c = mCam.counter();
  p.drawText(20,120, QString("good %1 / invalid %2 / missing %3").arg(c.framesGood).arg(c.framesInvalid).arg(c.framesMissing));

}

void LadyWidget::keyPressEvent(QKeyEvent * event)
{
	switch (event->key())
	{
		case Qt::Key_Space:
			// start recording
      mCam.startRecording(mStreamName);
			break;
		
		case Qt::Key_C:
      //mColor = !mColor;
      {
        int cammask;
        bool color;
        int interval;
        mCam.previewSettings(cammask, color, interval);
        mCam.setPreviewSettings(cammask, !color, interval);
      }
			break;

    case Qt::Key_R:
      mCam.counter().reset();
      break;

    case Qt::Key_Comma:
    case Qt::Key_Period:
      {
        bool autoControl;
        int quality, usage;
        mCam.jpegCompression(autoControl, quality, usage);
        usage += (event->key() == Qt::Key_Period ? 10 : -10);
        if (usage > 127) usage = 127;
        if (usage < 0) usage = 0;
        mCam.setJpegCompression(autoControl, quality, usage);
      }
      break;

    case Qt::Key_1:
    case Qt::Key_2:
    case Qt::Key_3:
    case Qt::Key_4:
    case Qt::Key_5:
    case Qt::Key_6:
      {
        int cam = event->key() - Qt::Key_1;
        int cammask;
        bool color;
        int interval;
        mCam.previewSettings(cammask, color, interval);
        if ( (cammask >> cam) & 1)
          cammask &= ~(1 << cam);
        else
          cammask |= (1 << cam);
        mCam.setPreviewSettings(cammask, color, interval);
      }
      break;

    case Qt::Key_PageUp:
    case Qt::Key_PageDown:
      {
        int cammask;
        bool color;
        int interval;
        mCam.previewSettings(cammask, color, interval);
        interval += (event->key() == Qt::Key_PageUp ? 10 : -10);
        mCam.setPreviewSettings(cammask, color, interval);
      }
      break;

		case Qt::Key_Escape:
			// stop recording
      mCam.stopRecording();
			break;
	}
}
			

void LadyWidget::updateFps()
{
	mFps = mFrames;
	mMBps = mMBytes;
	mFrames = 0;
	mMBytes = 0;
  update();
}

void LadyWidget::receivedFrame(LadybugFrame frame)
{
  if (frame.valid)
  {
    mMBytes += (double) frame.frameBytes / (1024 * 1024);
    mFrames++;
  }

  // TODO: save the frame also if it doesn't contain preview, just because of info
  if (frame.hasPreview)
  {
  mLastFrame = frame;
  update();
  }
}
