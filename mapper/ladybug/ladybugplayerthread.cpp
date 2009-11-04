/******************************************************************************
 *   Copyright (c) 2009 Martin Dobias
 *
 *   This program is free software; you can redistribute it and/or modify
 *   it under the terms of the GNU General Public License as published by
 *   the Free Software Foundation; either version 2 of the License, or
 *   (at your option) any later version.
 ******************************************************************************/

#include "ladybugplayerthread.h"

#include "ladybugimage.h"
#include "ladybugstream.h"

LadybugPlayerThread::LadybugPlayerThread(LadybugStream& stream)
  : mStopping(false), mStream(stream)
{
  mCameras = 0; // no cameras
  for (int c = 0; c < 6; c++)
    mZooms[c] = 1; // no zoom
}


void LadybugPlayerThread::run()
{
  // fill in a buffer with loaded, decoded frames
  // when full: sleep

  LadybugImage image;

  while (!shouldStop())
  {
    mStreamMutex.lock();
    bool res = mStream.readNextFrame(image);
    mStreamMutex.unlock();
    if (!res)
    {
      printf("end of stream!\n");
      stopPlayer();
      break;
    }

    if (image.isValid())
    {
      // we have a valid frame - decode and enqueue it
      processImage(mStream.currentFrame(), image);
    }
    else
    {
      fprintf(stderr, "read invalid image\n");
    }

    // if our buffer is full, take rest
    while (bufferCount() >= 5 && !shouldStop())
    {
      fprintf(stderr, "buffer full, sleeping\n");
      msleep(20);
    }
  }

  // enqueue invalid frame to signal that we've finished
  mBufferMutex.lock();
  LadybugPlayerFrame invalidFrame;
  invalidFrame.frameId = -1;
  mBuffer.enqueue(invalidFrame);
  mHasFrame.wakeOne();
  mBufferMutex.unlock();
}

void LadybugPlayerThread::processImage(int frameId, LadybugImage& image)
{
  LadybugPlayerFrame playerFrame;
  playerFrame.frameId = frameId;
  playerFrame.time = image.time();

  // decode images
  for (int c = 0; c < 6; c++)
  {
    int pow_scale = (mZooms[c] > 1 ? 0 : 1);

    if (mCameras & (1 << c))
      playerFrame.imgs[c] = image.getColorImage(c, true, pow_scale);
    else
      playerFrame.imgs[c] = QImage();
  }

  // add to the buffer
  mBufferMutex.lock();
  mBuffer.enqueue(playerFrame);
  fprintf(stderr, "enqueued frame (%d)\n", mBuffer.count());
  mHasFrame.wakeOne(); // signal we have a frame (in case there was none)
  mBufferMutex.unlock();
}

int LadybugPlayerThread::bufferCount()
{
  QMutexLocker lock(&mBufferMutex);
  return mBuffer.count();
}

LadybugPlayerFrame LadybugPlayerThread::getFrame()
{
  mBufferMutex.lock();

  // if there's no image in buffer, wait for it
  if (mBuffer.isEmpty())
  {
    fprintf(stderr, "waiting for frame\n");
    mHasFrame.wait(&mBufferMutex);
    fprintf(stderr, "done waiting for frame\n");
  }

  LadybugPlayerFrame frame = mBuffer.dequeue();
  mBufferMutex.unlock();
  return frame;
}


bool LadybugPlayerThread::shouldStop()
{
  QMutexLocker lock(&mStoppingMutex);
  return mStopping;
}

void LadybugPlayerThread::stopPlayer()
{
  QMutexLocker lock(&mStoppingMutex);
  mStopping = true;
}

void LadybugPlayerThread::seekToFrame(int frameId)
{
  QMutexLocker lockB(&mBufferMutex);
  mBuffer.clear();

  QMutexLocker lock(&mStreamMutex);
  mStream.seekToFrame(frameId);
}
