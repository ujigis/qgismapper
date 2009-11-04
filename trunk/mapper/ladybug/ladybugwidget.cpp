/******************************************************************************
 *   Copyright (c) 2009 Martin Dobias
 *
 *   This program is free software; you can redistribute it and/or modify
 *   it under the terms of the GNU General Public License as published by
 *   the Free Software Foundation; either version 2 of the License, or
 *   (at your option) any later version.
 ******************************************************************************/

#include "ladybugwidget.h"

#include <QPainter>
#include <QSlider>
#include <QPushButton>
#include <QKeyEvent>

#include "ladybugimage.h"

#include "ladybugplayerthread.h"

#define NAVIGATION_RECT QRect(0,0,100,100)
#define PEN_WIDTH 2
#define IMG_WIDTH (384/2)
#define IMG_HEIGHT (512/2)

LadybugWidget::LadybugWidget(QWidget* parent)
  : QWidget(parent), mThread(NULL)
{
  mPaused = true;
  mHasImage = false;
  mStartTime = 0;

  mNextFrame = new LadybugPlayerFrame;
  mTimer.setSingleShot(true);
  connect(&mTimer, SIGNAL(timeout()), this, SLOT(updateVideoPlayback()));

  mPositions[4].size = 1;
  mPositions[0].size = 1;
  mPositions[1].size = 1;

  mSlider = NULL;
  mPauseButton = NULL;

/*
  mSlider = new QSlider(Qt::Horizontal, this);
  mSlider->setGeometry(130, 10, 300, 20);
  mSlider->setPageStep(10);
  connect(mSlider, SIGNAL(valueChanged(int)), this, SLOT(seek(int)));

  mPauseButton = new QPushButton("|>", this);
  mPauseButton->setGeometry(100, 10, 20,20);
  connect(mPauseButton, SIGNAL(clicked()), this, SLOT(pause()));
*/
}

LadybugWidget::~LadybugWidget()
{
  // make sure the thread gets stopped and stream closed
  closeStream();

  delete mNextFrame;
}

QSize LadybugWidget::sizeHint () const
{
  return QSize(5*IMG_WIDTH, IMG_HEIGHT + 2*PEN_WIDTH);
}

void LadybugWidget::updateVideo(LadybugPlayerFrame f)
{
  // invalid frame?
  if (f.frameId == -1)
    return;

  mCurrentFrame = f.frameId;
  mCurrentTime = f.time;
  for (int i = 0; i < 6; i++)
    mImgs[i] = f.imgs[i];

  mHasImage = true;
  if (mSlider)
    mSlider->setValue( mCurrentFrame );
  update(); // trigger refresh
}

uint LadybugWidget::cameraMask()
{
  uint cams = 0;
  for (int c = 0; c < CAMERAS; c++)
    if (mPositions[c].size != -1)
      cams |= (1 << c);
  return cams;
}

bool LadybugWidget::cameraState(int cam)
{
  if (cam < 0 || cam >= 6)
    return false;
  return (mPositions[cam].size == 1);
}

void LadybugWidget::setCameraState(int cam, bool on)
{
  if (cam < 0 || cam >= 6)
    return;
  mPositions[cam].size = (on ? 1 : -1);

  // update the information in thread
  if (mThread)
    mThread->setCameras(cameraMask());
}

void LadybugWidget::setCameraZoom(int cam, double zoom, QPointF offset)
{
  if (cam < 0 || cam >= 6)
    return;

  mPositions[cam].zoom = zoom;
  
  // sanity check for offset values
  if (offset.x() < 0) offset.setX(0);
  if (offset.y() < 0) offset.setY(0);
  if (offset.x() + IMG_WIDTH/zoom > IMG_WIDTH)   offset.setX(IMG_WIDTH-IMG_WIDTH/zoom);
  if (offset.y() + IMG_HEIGHT/zoom > IMG_HEIGHT) offset.setY(IMG_HEIGHT-IMG_HEIGHT/zoom);
  mPositions[cam].offset = offset;

  if (mThread)
    mThread->setZoom(cam, mPositions[cam].zoom);
}

double LadybugWidget::cameraZoom(int cam, QPointF* offset)
{
  if (cam < 0 || cam >= 6)
    return -1;

  if (offset)
    *offset = mPositions[cam].offset;

  return mPositions[cam].zoom;
}


bool LadybugWidget::openStream(QString baseName)
{
  bool res = mStream.openForReading(baseName);
  if (!res)
    return false;
  if (mSlider)
    mSlider->setRange(0, mStream.framesCount()-1);

  // show first frame
  LadybugPlayerFrame f = getSingleFrame(0);
  mStartTime = f.time;
  updateVideo(f);

  return true;
}

void LadybugWidget::stopPlayerThread()
{
  if (mThread && mThread->isRunning())
  {
    mThread->stopPlayer();
    mThread->wait(); // wait until the thread ends
    fprintf(stderr, "player thread ended\n");
  }
  delete mThread;
  mThread = NULL;
}

bool LadybugWidget::closeStream()
{
  stopPlayerThread();

  mHasImage = false;
  update();
  return mStream.close();
}

LadybugPlayerFrame LadybugWidget::getSingleFrame(int frameId)
{

  LadybugImage image;
  // go to the frame
  mStream.seekToFrame(frameId);
  // fetch the frame
  bool res = mStream.readNextFrame(image);

  if (!res)
  {
    LadybugPlayerFrame invalidFrame;
    invalidFrame.frameId = -1;
    return invalidFrame;
  }

  LadybugPlayerFrame playerFrame;
  playerFrame.frameId = mStream.currentFrame();
  playerFrame.time = image.time();

  // decode images
  for (int c = 0; c < 6; c++)
  {
    int pow_scale = (cameraZoom(c) > 1 ? 0 : 1);

    if (cameraState(c))
      playerFrame.imgs[c] = image.getColorImage(c, true, pow_scale);
    else
      playerFrame.imgs[c] = QImage();
  }

  return playerFrame;
}

void LadybugWidget::drawNavigation(QPainter& p)
{
  QColor color;
  QPolygon arrow;
  arrow << QPoint(-5, 0) << QPoint(5,0) << QPoint(0,-10);
  p.save();
  p.setRenderHint(QPainter::Antialiasing);
  p.translate(NAVIGATION_RECT.center());
  for (int i = 0; i < 5; i++)
  {
    p.save();
    p.rotate(i*360/5);
    p.translate(0,-16);
    color = ( cameraState(i) ? QColor::fromHsv(i*360/5, 255,255) : Qt::lightGray);
    p.setBrush(color);
    p.setPen(color.darker());
    p.drawPolygon(arrow);
    p.restore();
  }
  p.setBrush(Qt::black);
  p.drawEllipse(-5,-5,11,11);
  p.restore();
}

void LadybugWidget::paintEvent(QPaintEvent* /* event */)
{
  QPainter p(this);

  if (!mHasImage)
  {
    p.drawLine(0,0, width(), height());
    p.drawLine(width(),0, 0, height());
    return;
  }

  QRect srcRect;
  int x = 0;
  p.save();
  p.translate(100,1);
  for (int c = 0; c < CAMERAS; c++)
  {
    int cam = (c+3) % CAMERAS;
    if (cam == 5) // top cam - skip
      continue;

    if (cameraState(cam))
    {
      QColor color = QColor::fromHsv(cam*72, 255,255);
      p.setPen(QPen(color, PEN_WIDTH));

      p.drawRect(x,0, IMG_WIDTH + PEN_WIDTH, IMG_HEIGHT + PEN_WIDTH);
      QPointF offset;
      double zoom = cameraZoom(cam, &offset);
      printf("draw: zoom %.2f -- off %.1f,%.1f -- %.1f x %.1f\n", zoom, offset.x(), offset.y(), IMG_WIDTH/zoom, IMG_HEIGHT/zoom);

      // prepare source rectangle - usually a window from the image
      // additionally image can be scaled for better details when zoomed in
      int imgScale = mImgs[cam].width() / IMG_WIDTH;
      QSize imgSize = QSize(IMG_WIDTH/zoom, IMG_HEIGHT/zoom) * imgScale;
      QPoint imgOffset = offset.toPoint() * imgScale;
      srcRect = QRect(imgOffset, imgSize);

      p.drawImage(QRect(x+PEN_WIDTH/2, PEN_WIDTH/2, IMG_WIDTH, IMG_HEIGHT), mImgs[cam], srcRect);
      x += IMG_WIDTH + PEN_WIDTH*3;
    }
  }
  p.restore();

  // draw info
  drawNavigation(p);

  p.setPen(QColor(255,0,0));

  p.drawText(20,120, QString("%1 / %2").arg(mCurrentFrame).arg(mStream.framesCount()) );
  p.drawText(20,140, QString::number((mCurrentTime-mStartTime)/1000.0, 'f', 3) + " s");
}

void LadybugWidget::seekToFrame(int frameId)
{
  if (frameId < 0)
    frameId = 0;

  if (frameId == mCurrentFrame)
    return;

  printf("SEEK! %d\n", frameId);

  if (mPaused)
  {
    updateVideo(getSingleFrame(frameId));
  }
  else
  {
    mThread->seekToFrame(frameId);
  }
  update();
}

void LadybugWidget::seekToTime(uint msecs)
{
  mStream.seekToTime(msecs);
  int frameId = mStream.currentFrame();
  printf("frame id: %d\n", frameId);

  if (mPaused)
  {
    updateVideo(getSingleFrame(frameId));
  }
  else
  {
    mThread->seekToFrame(frameId);
  }
  update();
}


void LadybugWidget::keyPressEvent(QKeyEvent* e)
{
  if (e->key() >= Qt::Key_1 && e->key() <= Qt::Key_5)
  {
    int i = e->key()-Qt::Key_1;

    // invert camera on/off setting
    setCameraState(i, !cameraState(i));

    if (mPaused)
      updateVideo(getSingleFrame(mCurrentFrame));
  }

  switch (e->key())
  {
    case Qt::Key_Space:
      pause();
      break;
    case Qt::Key_Left:
      seekToFrame(mCurrentFrame-1);
      break;
    case Qt::Key_Right:
      seekToFrame(mCurrentFrame+1);
      break;
    case Qt::Key_Home:
      seekToFrame(0);
      break;
    case Qt::Key_End:
      seekToFrame(mStream.framesCount()-1);
      break;
    case Qt::Key_PageUp:
      seekToFrame(mCurrentFrame-25);
      break;
    case Qt::Key_PageDown:
      seekToFrame(mCurrentFrame+25);
      break;

    // %%% seek to random position (for testing)
    case Qt::Key_S:
      {
        uint msecs = random() % (mStream.framesCount() / 15 * 1000);
        printf("RANDOM TIME SEEK! %d ms\n", msecs);
        seekToTime(msecs);
        break;
      }
  }
}

void LadybugWidget::closeEvent(QCloseEvent* event)
{
  // make sure to stop playback
  if (!mPaused)
    pause();

  QWidget::closeEvent(event);
}

void LadybugWidget::pause()
{
  mPaused = !mPaused;

  if (mPaused)
  {
    mTimer.stop();
    mPlaybackStartTime = QTime();

    // terminate thread
    stopPlayerThread();

    // make sure we're where we paused the video
    updateVideo(getSingleFrame(mCurrentFrame));
  }
  else
  {
    // create thread, pass the stream
    mThread = new LadybugPlayerThread(mStream);
    mThread->setCameras(cameraMask());
    mThread->start();

    // in update routine: show frame + get next frame + run timer
    updateVideoPlayback();
  }

  if (mPauseButton)
    mPauseButton->setText(mPaused ? "|>" : "||");
}

void LadybugWidget::updateVideoPlayback()
{
  if (mPlaybackStartTime.isNull())
  {
    // we're starting playback
    mPlaybackStartTime.start();
    mPlaybackFirstFrameTime = mCurrentTime;
  }
  else
  {
    // draw prepared frame
    updateVideo(*mNextFrame);
  }

  // get next frame
  *mNextFrame = mThread->getFrame();

  if (mNextFrame->frameId == -1)
  {
    // the thread has finished... we're pausing!
    pause();
    return;
  }

  // find out waiting time + run timer
  int timeElapsed = mPlaybackStartTime.elapsed();
  int timeNext = (mNextFrame->time - mPlaybackFirstFrameTime);
  int waitTime = timeNext-timeElapsed;
  printf("wait time %d\n", waitTime);

  // make sure we set a valid interval
  if (waitTime <= 0)
    waitTime = 1;

  mTimer.start(waitTime);
}

void LadybugWidget::wheelEvent(QWheelEvent* e)
{
  for (int cam = 0; cam < CAMERAS; cam++)
  {
    QRect r = cameraRect(cam);
    if (r.contains(e->pos()))
    {
      QPointF oldOffset;
      double oldZoom = cameraZoom(cam, &oldOffset);
      // negative = zoom in
      const double FACTOR = 1.25;
      double zoom = oldZoom * (e->delta() > 0 ? 1/FACTOR : FACTOR);
      if (zoom < 1) zoom = 1;
      if (zoom > 4) zoom = 4;
      if (zoom == oldZoom) return;

      QPointF pos = (e->pos()-r.topLeft())/oldZoom;
      QPointF newPos = pos * oldZoom/zoom;
      QPointF offset = oldOffset + pos - newPos;

      printf("delta %d | pos %.1f,%.1f | new_pos %.1f,%.1f | zoom %.2f | offset %.1f,%.1f\n", e->delta(), pos.x(),pos.y(), newPos.x(), newPos.y(), zoom, offset.x(), offset.y());

      setCameraZoom(cam, zoom, offset);
      if (mPaused)
        updateVideo(getSingleFrame(mCurrentFrame));
      break;
    }
  }

}

void LadybugWidget::mousePressEvent(QMouseEvent* e)
{
  if (NAVIGATION_RECT.contains(e->pos()))
  {
    // handle navigation
    navigationMousePress(e);
  }
  else
  {
    // handle images from cameras

    // we're interested only to right click - reset zoom
    if (e->button() != Qt::RightButton)
      return;

    for (int i = 0; i < CAMERAS; i++)
    {
      if (cameraRect(i).contains(e->pos()))
      {
        setCameraZoom(i, 1);
        if (mPaused)
          updateVideo(getSingleFrame(mCurrentFrame));
        break;
      }
    }
  }
}

void LadybugWidget::navigationMousePress(QMouseEvent* e)
{
  QRect arrowRect = QRect(QPoint(-5, 0), QPoint(5, -10));

  QPoint centerPt = NAVIGATION_RECT.center();
  QMatrix m;
  m.translate(centerPt.x(), centerPt.y());

  for (int i = 0; i < 5; i++)
  {
    QMatrix m2 = m;
    m2.rotate(i*360/5);
    m2.translate(0,-16);

    QPoint resPt = m2.inverted().map(e->pos());
    if (arrowRect.contains(resPt))
    {
      // invert camera on/off setting
      setCameraState(i, !cameraState(i));

      if (mPaused)
        updateVideo(getSingleFrame(mCurrentFrame));
    }
  }
}

QRect LadybugWidget::cameraRect(int camRequested)
{
  if (!cameraState(camRequested))
    return QRect();

  QPoint topleft = QPoint(100,1) + QPoint(PEN_WIDTH/2,PEN_WIDTH/2);

  for (int c = 0; c < CAMERAS; c++)
  {
    int cam = (c+3) % CAMERAS;
    if (cam == 5) // top cam - skip
      continue;

    if (cam == camRequested) // we're done!
      break;

    if (cameraState(cam))
      topleft += QPoint(IMG_WIDTH + PEN_WIDTH*3, 0);
  }

  return QRect(topleft, QSize(IMG_WIDTH, IMG_HEIGHT));
}
