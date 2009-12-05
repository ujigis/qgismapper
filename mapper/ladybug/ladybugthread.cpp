/******************************************************************************
 *   Copyright (c) 2009 Martin Dobias
 *
 *   This program is free software; you can redistribute it and/or modify
 *   it under the terms of the GNU General Public License as published by
 *   the Free Software Foundation; either version 2 of the License, or
 *   (at your option) any later version.
 ******************************************************************************/

#include "ladybugthread.h"

#include "ladybugimage.h"
//#include "ladybug.h"

#include <QTime>

#ifndef WIN32
#include <arpa/inet.h>
#else
#include <winsock.h>
#endif

#define MAX_QUEUE   64

LadybugThread::LadybugThread(Ladybug& cam)
: mStopping(false), camera(NULL), mCam(cam)
{
    mPreviewCamMask = 1 << 2; // third camera only when starting
    mPreviewColor = false;
    mPreviewInterval = 100; // 100 ms
}

void LadybugThread::run()
{
#ifndef WIN32
    dc1394error_t err;
    dc1394video_frame_t *frame;

    LadybugImage image;

    bool first = true;
    //int i = 0;

    mPreviewTime.start();

    int lastSequenceId = 0;

    while (!shouldStop())
    {

        // dequeue (capture) frame
        mCameraMutex.lock();
        err=dc1394_capture_dequeue(camera, DC1394_CAPTURE_POLICY_WAIT, &frame);
        mCameraMutex.unlock();
        if (err != DC1394_SUCCESS)
        {
            // TODO: report error
            printf("capture dequeue error!\n");
            continue;
        }

        //printf("img %d elapsed | %d ms | behind %d\n", i++, t.elapsed(), frame->frames_behind);

        // initialize image, don't transfer ownership (owned by dc1394)
        image.setData(frame->image, frame->image_bytes, false);

        //double time = image.timeSec() + image.timeMicroSec() / 1000000.0;
        //printf("seq # %d  | %10.3f\n", image.sequenceId(), time );

        LadybugFrame f;
        f.framesBehind = frame->frames_behind;
        f.valid = image.isValid();

        if (!image.isValid())
        {
          // the frame is completely invalid - even the signature wasn't recognized
          // or the header is correct but some images are corrupted (bad JFIF header)
          // we shouldn't rely on these frames either
          mCam.counter().framesInvalid++;
          //printf("invalid frame\n");
        }
        else
        {
          mCam.counter().framesGood++;

          if (first)
          {
            // currently the only way how I can find out serial number of head
            uint32 serial = *(uint32*)(frame->image + 0x54);
            mCam.setSerialHead( ntohl(serial) );
            printf("serial head: %u\n", ntohl(serial) );
            first = false;
          }
          else
          {
            mCam.counter().framesMissing += (image.sequenceId() - lastSequenceId - 1);
          }

          processFrame(f, image);
          emit capturedFrame(f);

          lastSequenceId = image.sequenceId();
        }

        mCameraMutex.lock();
        err=dc1394_capture_enqueue(camera, frame);
        mCameraMutex.unlock();
        if (err != DC1394_SUCCESS)
        {
            // TODO: report error
            printf("capture enqueue error!\n");
        }
    }

    printf("thread terminated correctly ;-)\n");
#endif
}

bool LadybugThread::shouldStop()
{
    QMutexLocker lock(&mStoppingMutex);
    return mStopping;
}

void LadybugThread::stopCapture()
{
    QMutexLocker lock(&mStoppingMutex);
    mStopping = true;
}

void LadybugThread::setPreviewSettings(int camMask, bool color, int interval)
{
  QMutexLocker lock(&mSettingsMutex);
  mPreviewCamMask = camMask;
  mPreviewColor = color;
  mPreviewInterval = interval;
  if (mPreviewInterval < 0) mPreviewInterval = 0;
}

void LadybugThread::previewSettings(int& camMask, bool& color, int& interval)
{
  QMutexLocker lock(&mSettingsMutex);
  camMask = mPreviewCamMask;
  color = mPreviewColor;
  interval = mPreviewInterval;
}

void LadybugThread::processFrame(LadybugFrame& f, LadybugImage& image)
{
    // do the recording if turned on
    if (isRecording())
    {
      mRecordingThread.writeImage( image ); // copy data!
      f.megabytesWritten = mRecordingThread.megabytesWritten();
      f.framesWritten = mRecordingThread.framesCount();
      f.framesDiscarded = mRecordingThread.framesDiscarded();
    }
    else
    {
      f.megabytesWritten = 0;
      f.framesWritten = 0;
      f.framesDiscarded = 0;
    }

    int camMask;
    bool color;
    int interval;
    previewSettings(camMask, color, interval);

    // create new preview image only after some timeout and only from good data
    if (mPreviewTime.elapsed() >= interval)
    {
      f.hasPreview = TRUE;

      // generate previews
      for (int i = 0; i < 6; i++)
      {
        if ( !( (camMask >> i) & 1) )
          continue;

        if (color)
          f.preview[i] = image.getColorImage(i, true, 1);
        else
          f.preview[i] = image.getChannelImage(i, 0, true, 1);

        if (f.preview[i].isNull())
        {
          printf("preview failed!\n");
          //image.dump();
        }
      }
      // restart the counter
      mPreviewTime.restart();
    }

    f.frameBytes = image.frameBytes();
}

LadybugInfo LadybugThread::cameraInfo()
{
    mCameraMutex.lock();

    LadybugInfo info;
    info.calibration = mCam.fetchCalibration();
    info.serialBase = mCam.serialNumBase();
    info.serialHead = mCam.serialNumHead();

    mCameraMutex.unlock();
    return info;
}

void LadybugThread::startRecording(QString streamName)
{
  if (isRecording())
    return;

  // TODO: check result
  mRecordingThread.startRecording(streamName, cameraInfo());
}

void LadybugThread::stopRecording()
{
  if (!isRecording())
    return;

  // TODO: check result
  mRecordingThread.stopRecording();

  // wait for the thread to terminate (max 3 secs)
  if (mRecordingThread.wait(3000))
  {
    printf("done waiting for recording thread ;-)\n");
  }
  else
  {
    mRecordingThread.terminate();
    printf("had to terminate recording thread :-(\n");
  }
}

bool LadybugThread::isRecording()
{
  return mRecordingThread.isRecording();
}

void LadybugThread::setCurrentGpsInfo(LadybugGpsInfo& gpsInfo)
{
  mRecordingThread.setCurrentGpsInfo(gpsInfo);
}


//--------------------
// RECORDING THREAD

LadybugRecordingThread::LadybugRecordingThread()
{
  mRecording = false;
  mFramesDiscarded = 0;
}

bool LadybugRecordingThread::startRecording(QString streamName, LadybugInfo camInfo)
{
  QMutexLocker lock(&mRecordingMutex);
  if (!mRecording)
  {
    if (mStream.openForWriting(streamName, camInfo))
    {
      mRecording = TRUE;
      mFramesDiscarded = 0;
      // let's start the recording thread
      start();
      return true;
    }
  }
  return false;
}

bool LadybugRecordingThread::stopRecording()
{
  mRecordingMutex.lock();
  if (!mRecording)
  {
    mRecordingMutex.unlock();
    return false;
  }

  // tell it to stop
  mRecording = FALSE;
  // signal new image to get out of the wait condition
  mNewImage.wakeOne();
  mRecordingMutex.unlock();

  return true;
}

bool LadybugRecordingThread::isRecording()
{
  QMutexLocker lock(&mRecordingMutex);
  return mRecording;
}

void LadybugRecordingThread::run()
{
  while (isRecording())
  {
    // fetch image from queue
    mRecordingMutex.lock();

    if (mImageQueue.isEmpty())
    {
      mNewImage.wait(&mRecordingMutex); // wait for some new frames

      // it seems we're going to finish
      mRecordingMutex.unlock();
      continue;
    }

    LadybugImage* img = mImageQueue.dequeue();
    mRecordingMutex.unlock();

    // write image to stream - this is the lengthy operation
    mStream.writeImage(*img);

    // we're not going to need it anymore - delete it!
    delete img;
  }

  mRecordingMutex.lock();
  mStream.close();

  // release the rest of the images in queue
  while (!mImageQueue.isEmpty())
    delete mImageQueue.dequeue();
  mRecordingMutex.unlock();
}

void LadybugRecordingThread::writeImage(LadybugImage& img)
{
  QMutexLocker lock(&mRecordingMutex);

  LadybugImage* i2 = new LadybugImage(img);

  // add gps info (if available)
  if (mLastGpsInfo.isValid())
    i2->addGpsData(mLastGpsInfo.getGPGGA());
  // add padding bytes
  i2->addPadding();

  mImageQueue.enqueue(i2);

  fprintf(stderr, "in queue: %d\n", mImageQueue.count());

  if (mImageQueue.count() > MAX_QUEUE)
  {
    // our queue is too big. select a random frame from queue and remove it
    int at = random() % mImageQueue.count();
    fprintf(stderr, "queue full, discarding a frame! (%d)\n", at);
    delete mImageQueue.takeAt(at);
    mFramesDiscarded++;
  }

  mNewImage.wakeOne();

}

void LadybugRecordingThread::setCurrentGpsInfo(LadybugGpsInfo& gpsInfo)
{
  QMutexLocker lock(&mRecordingMutex);

  mLastGpsInfo = gpsInfo;

  // TODO: probably remove
  //mStream.setCurrentGpsInfo(gpsInfo);
}
