/******************************************************************************
 *   Copyright (c) 2009 Martin Dobias
 *
 *   This program is free software; you can redistribute it and/or modify
 *   it under the terms of the GNU General Public License as published by
 *   the Free Software Foundation; either version 2 of the License, or
 *   (at your option) any later version.
 ******************************************************************************/

#ifndef LADYBUG_H
#define LADYBUG_H

class LadybugPrivate;

#include <QImage>

#include <QObject>

typedef unsigned int uint32;

//class LadybugFrame;



class LadybugFrame
{

public:
  LadybugFrame() : framesBehind(0),valid(FALSE),
    frameBytes(0), hasPreview(FALSE), megabytesWritten(0), framesWritten(0) { for (int i=0; i<6; i++) preview.append(QImage()); }

  QImage previewImage(int cam) { return preview.at(cam); }

  int framesBehind;
  bool valid;
  unsigned int frameBytes;
  bool hasPreview;
  QList<QImage> preview; //[6];

  double megabytesWritten;
  int framesWritten;
};

//Q_DECLARE_METATYPE(LadybugFrame)

class LadybugCounter
{
public:
  LadybugCounter() { reset(); }
  void reset() { framesGood = 0; framesInvalid = 0; framesMissing = 0; }

  int framesGood; // correctly received frames
  int framesInvalid; // completely invalid or partially corrupted frames
  int framesMissing; // frames from the sequence not caught
};

class Ladybug : public QObject
{
    Q_OBJECT

public:
	Ladybug();
	~Ladybug();
	
	bool init();
	
	bool exit();

  bool isActive() const;

  QString errorMessage();
	
  void setSerialHead(uint32 serial);

  QByteArray fetchCalibration();
	
        uint32 serialNumBase();
        uint32 serialNumHead();

  void startRecording(QString streamName);
  void stopRecording();
  bool isRecording();

  void setPreviewSettings(int camMask, bool color, int interval);
  void previewSettings(int& camMask, bool& color, int& interval);

  bool setJpegCompression(bool autoControl, int jpgQuality, int bufferUsage);
  bool jpegCompression(bool& autoControl, int& jpgQuality, int& bufferUsage);

  LadybugCounter& counter();

public slots:
    void receivedFrame(LadybugFrame frame);

signals:
    void capturedFrame(LadybugFrame frame);
	
private:
  LadybugPrivate* d;

};

#endif
