/******************************************************************************
 *   Copyright (c) 2009 Martin Dobias
 *
 *   This program is free software; you can redistribute it and/or modify
 *   it under the terms of the GNU General Public License as published by
 *   the Free Software Foundation; either version 2 of the License, or
 *   (at your option) any later version.
 ******************************************************************************/

#ifndef LADYBUGWIDGET_H
#define LADYBUGWIDGET_H

#include <QWidget>
#include <QTimer>
#include <QImage>
#include <QTime>

class QSlider;
class QPushButton;

class LadybugPlayerThread;
class LadybugPlayerFrame;

#include "ladybugstream.h"

#define CAMERAS   6

class LadybugWidget : public QWidget
{
  Q_OBJECT

public:
  LadybugWidget(QWidget* parent = NULL);

  ~LadybugWidget();

  bool openStream(QString baseName);

  bool closeStream();

  class CameraPosition
  {
    public:
    CameraPosition(): offset(0,0), size(-1), zoom(1) {}
    QPointF offset;
    int size;
    double zoom;
  };

  virtual QSize sizeHint () const;

public slots:
  void seekToFrame(int frameId);
  void seekToTime(uint msecs);
  void pause();
  void updateVideoPlayback();

protected:
  void paintEvent(QPaintEvent* e);
  void keyPressEvent(QKeyEvent* e);
  void closeEvent(QCloseEvent* event);
  void wheelEvent(QWheelEvent* e);
  void mousePressEvent(QMouseEvent* event);

  uint cameraMask();
  void setCameraState(int cam, bool on);
  bool cameraState(int cam);
  QRect cameraRect(int cam);
  void setCameraZoom(int cam, double zoom, QPointF offset = QPointF());
  double cameraZoom(int cam, QPointF* offset = NULL);

  LadybugPlayerFrame getSingleFrame(int frameId);
  void updateVideo(LadybugPlayerFrame f);
  void stopPlayerThread();

  void drawNavigation(QPainter& p);
  void navigationMousePress(QMouseEvent* e);

protected:
  LadybugStream mStream;
  int mCurrentFrame;
  uint mCurrentTime, mStartTime;
  bool mPaused;
  QTimer mTimer;
  QImage mImgs[6];
  bool mHasImage;

  QTime mPlaybackStartTime;
  uint mPlaybackFirstFrameTime;
  LadybugPlayerFrame* mNextFrame;

  QSlider* mSlider;
  QPushButton* mPauseButton;

  CameraPosition mPositions[CAMERAS];
  LadybugPlayerThread* mThread;
};

#endif // LADYBUGWIDGET_H
