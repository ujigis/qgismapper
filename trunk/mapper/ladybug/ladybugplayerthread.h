/******************************************************************************
 *   Copyright (c) 2009 Martin Dobias
 *
 *   This program is free software; you can redistribute it and/or modify
 *   it under the terms of the GNU General Public License as published by
 *   the Free Software Foundation; either version 2 of the License, or
 *   (at your option) any later version.
 ******************************************************************************/

#ifndef LADYBUGPLAYERTHREAD_H
#define LADYBUGPLAYERTHREAD_H

#include <QThread>
#include <QMutex>
#include <QWaitCondition>

#include <QQueue>
#include <QImage>

class LadybugImage;
class LadybugStream;

class LadybugPlayerFrame
{
  public:
    int frameId;
    uint time; // in miliseconds
    QImage imgs[6];
};

class LadybugPlayerThread : public QThread
{
public:
    LadybugPlayerThread(LadybugStream& stream);

    /** thread procedure */
    void run();

    void setCameras(ulong cameras) { mCameras = cameras; }
    void setZoom(int camera, double zoom) { if (camera >= 0 && camera < 6) mZooms[camera] = zoom; }

    void stopPlayer();

    int bufferCount();

    LadybugPlayerFrame getFrame();

    void seekToFrame(int frameId);

protected:
    void processImage(int frameId, LadybugImage& image);
    bool shouldStop();


    bool mStopping;
    QMutex mStoppingMutex;

    QQueue<LadybugPlayerFrame> mBuffer;
    QMutex mBufferMutex;
    QWaitCondition mHasFrame;

    QMutex mStreamMutex;
    LadybugStream& mStream;

    ulong mCameras;
    double mZooms[6];
};

#endif // LADYBUGPLAYERTHREAD_H
