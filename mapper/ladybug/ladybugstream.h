/******************************************************************************
 *   Copyright (c) 2009 Martin Dobias
 *
 *   This program is free software; you can redistribute it and/or modify
 *   it under the terms of the GNU General Public License as published by
 *   the Free Software Foundation; either version 2 of the License, or
 *   (at your option) any later version.
 ******************************************************************************/

#ifndef LADYBUGSTREAM_H
#define LADYBUGSTREAM_H

#include <QFile>
#include <QMap>
#include <QDateTime>

typedef unsigned int uint32;

class LadybugImage;


// a simple class containing info necessary for stream writing
class LadybugInfo
{
public:
    LadybugInfo() : calibration(), serialBase(0), serialHead(0) {}
    bool isValid() { return serialBase != 0 && calibration.length() != 0; }

    QByteArray calibration;
    uint32 serialBase;
    uint32 serialHead;
};

/**
 Class that contains information about GPS status.

 Ladybug SDK seems not to use the GPS summary at the end of the file.
 Instead it's necessary to add recent NMEA sentences at the end of each image frame.
 */
class LadybugGpsInfo
{
public:
  LadybugGpsInfo(double lon_ = 0, double lat_ = 0, double alt_ = 0, QDateTime time_ = QDateTime())
    : lon(lon_), lat(lat_), alt(alt_), time(time_) {}

  bool isValid() const { return lon != 0 || lat != 0 || alt != 0; }
  QByteArray getGPGGA() const;

  double lon,lat,alt;
  QDateTime time;
};


class LadybugStream
{
public:
	LadybugStream();
	
  bool isOpen() const;
	
  bool close();

  enum Mode { Reading, Writing };

  Mode mode() const;

  // only for writing

  bool openForWriting(QString baseName, LadybugInfo cameraInfo, int fileIndex = 0);

  bool writeImage(const LadybugImage& image);
	
	double megabytesWritten() const;
	
  //! total number of frames in the whole stream
  ulong framesCount() const;

  // only for reading

  bool openForReading(QString baseName, int fileIndex = 0);

  bool readNextFrame(LadybugImage& image);

  bool seekToFrame(int frameId);

  bool seekToTime(unsigned int miliseconds);

  ulong currentFrame() const;

  void setCurrentGpsInfo(LadybugGpsInfo& gpsInfo);

  const LadybugInfo& cameraInfo() const;

protected:
  static QString pgrFilename(QString baseName, int index);

  static bool parseBaseNameAndIndex(QString filename, QString& outBaseName, int& outFileIndex);

  // when writing - continue with next file index
  bool startNextFile();

  // internal open
  bool openForWritingInternal(QString baseName, int fileIndex);

  bool openForReadingInternal(int fileIndex, int firstFrame);

  // seek to specific frame id and return its time in miliseconds
  uint frameTime(int frameId);

protected:
	QString mBaseName;
  int mFileIndex;
	QFile mFile;
  Mode mMode;

  LadybugInfo mCameraInfo; // r+w
  double mNumMegabytes; // w

  //! number of frames in this stream file
  int mNumFrames; // r+w
  //! number of frames in the whole stream
  int mTotalNumFrames;

  // index
  uint32 mOffsets[512]; // r+w
  int mOffsetCount; // r+w
  uint32 mIndexIncrement; // r+w

  int mCurrentFrame; // r
  uint32 mDataOffset; // r
  int mFirstFileIndex;
  int mTotalNumFiles;
  QList<int> mFirstFrameList;
  int mFirstFrame;

  // maps image number to gps info (not all images have gps info)
  QMap<int, LadybugGpsInfo> mGpsInfo;
};

#endif
