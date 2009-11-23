/******************************************************************************
 *   Copyright (c) 2009 Martin Dobias
 *
 *   This program is free software; you can redistribute it and/or modify
 *   it under the terms of the GNU General Public License as published by
 *   the Free Software Foundation; either version 2 of the License, or
 *   (at your option) any later version.
 ******************************************************************************/

#ifndef LADYBUGTHREAD_H
#define LADYBUGTHREAD_H

#include <QThread>

#include <QMutex>
#include <QTime>

#ifndef WIN32
#include <dc1394/dc1394.h>
#else
typedef void dc1394camera_t;
#endif

#include "ladybug.h"
#include "ladybugstream.h"

#include <QQueue>
#include <QWaitCondition>
class LadybugRecordingThread : public QThread
{
public:
    LadybugRecordingThread();

    bool startRecording(QString streamName, LadybugInfo info);
    bool stopRecording();

    bool isRecording();

    void run();

    void writeImage(LadybugImage& img);

    double megabytesWritten() const { return mStream.megabytesWritten(); }
    ulong framesCount() const { return mStream.framesCount(); }
    int framesDiscarded() const { return mFramesDiscarded; }

protected:
    QMutex mRecordingMutex;

    // these ones must be accessed with mRecordingMutex locked!
    bool mRecording;
    QQueue<LadybugImage*> mImageQueue;
    QWaitCondition mNewImage;

    // used only within the thread!
    LadybugStream mStream;

    // counter of discarded frames
    int mFramesDiscarded;
};


class LadybugThread : public QThread
{
    Q_OBJECT

public:
    LadybugThread(Ladybug& cam);

#ifndef WIN32
    void setCamera(dc1394camera_t *c) { camera = c; }
#endif

    /** thread procedure */
    void run();

    /** called by main thread to stop the thread */
    void stopCapture();

    bool shouldStop();

    void setPreviewSettings(int camMask, bool color, int interval);

    void previewSettings(int& camMask, bool& color, int& interval);

    void startRecording(QString streamName);
    void stopRecording();
    bool isRecording();

signals:
    void capturedFrame(LadybugFrame frame);

protected:

    void processFrame(LadybugFrame& f, LadybugImage& image);

    LadybugInfo cameraInfo();

    bool mStopping;
    QMutex mStoppingMutex;

    // these ones can be accessed only through setPreviewSettings / previewSettings
    int mPreviewCamMask;
    bool mPreviewColor;
    int mPreviewInterval;
    QMutex mSettingsMutex;

    QTime mPreviewTime;

    // these ones must be accessed with locked cameraMutex
    dc1394camera_t *camera;
    Ladybug& mCam;
    QMutex mCameraMutex;

    LadybugRecordingThread mRecordingThread;
};

#endif // LADYBUGTHREAD_H
