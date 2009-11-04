/******************************************************************************
 *   Copyright (c) 2009 Martin Dobias
 *
 *   This program is free software; you can redistribute it and/or modify
 *   it under the terms of the GNU General Public License as published by
 *   the Free Software Foundation; either version 2 of the License, or
 *   (at your option) any later version.
 ******************************************************************************/

#ifndef LADYWIDGET_H
#define LADYWIDGET_H

#include <QWidget>
#include <QPainter>
#include <QTimer>
#include <QList>

#include "ladybug.h"
#include "ladybugimage.h"
#include "ladybugstream.h"

class LadyWidget : public QWidget
{
	Q_OBJECT

public:
  LadyWidget(Ladybug& cam, QString streamName, QWidget* p=NULL);
	
	void paintEvent(QPaintEvent * event);
	
	void keyPressEvent(QKeyEvent * event);
	
public slots:
	void updateFps();

    void receivedFrame(LadybugFrame frame);
	
private:
	QList<QImage> mImgs;
	int mFrames;
	double mFps, mMBps, mMBytes;
	Ladybug& mCam;
	QTimer mT, mTfps;
	bool mColor;
  LadybugFrame mLastFrame;
  QString mStreamName;
};

#endif
