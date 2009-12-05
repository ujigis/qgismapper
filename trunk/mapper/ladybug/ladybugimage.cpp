/******************************************************************************
 *   Copyright (c) 2009 Martin Dobias
 *
 *   This program is free software; you can redistribute it and/or modify
 *   it under the terms of the GNU General Public License as published by
 *   the Free Software Foundation; either version 2 of the License, or
 *   (at your option) any later version.
 ******************************************************************************/

#include "ladybugimage.h"

#include "ladybug_pgr.h"

#include <QImage>
#include <QFile>
#include <QImageReader>
#include <QBuffer>

#ifndef WIN32
#include <arpa/inet.h>
#else
#include <winsock.h>
#endif

#define LADY_DEBUG

unsigned int big2little(unsigned int x)
{
	return ntohl(x);
}

unsigned int little2big(unsigned int x)
{
  return htonl(x);
}

// return offset and size of image in the data frame
static void jpegOffsetAndSize(unsigned char* data, int cam, int channel, uint& jpgoffset, uint& jpgsize)
{
  unsigned int adr=0x340+cam*32+(3-channel)*8;
  jpgoffset = big2little( *(unsigned int*)(data+adr) );
  adr+=4;
  jpgsize = big2little( *(unsigned int*)(data+adr) );
}

LadybugImage::LadybugImage()
 : mData(NULL), mBufferSize(0), mFrameSize(0), mOwnData(false)
{
}

LadybugImage::LadybugImage(unsigned char* data, unsigned int size, bool ownData)
 : mData(data), mBufferSize(size), mOwnData(ownData)
{
  mFrameSize = big2little( *(unsigned int*)(mData+8) );
}

LadybugImage::LadybugImage(const LadybugImage& other)
{
  mBufferSize = other.mBufferSize;
  mData = new unsigned char[mBufferSize];
  mOwnData = true;
  memcpy(mData, other.mData, mBufferSize);

  mFrameSize = other.mFrameSize;

  mAppendedData = other.mAppendedData;
}

void LadybugImage::setData(unsigned char* data, unsigned int size, bool ownData)
{
  if (mOwnData)
    delete [] mData;

  mData = data;
  mBufferSize = size;
  mOwnData = ownData;

  mFrameSize = big2little( *(unsigned int*)(mData+8) );
}

LadybugImage::~LadybugImage()
{
  // delete the data if we own them
  if (mOwnData)
  {
    delete [] mData;
  }
}


bool LadybugImage::isValid() const
{
  // this is a magic number... we need at least several kilobytes of data!
  if (mBufferSize < 0x1000)
		return false;

  // check whether this is a correct compressed ladybug frame
  if (big2little( *(unsigned int*)(mData+0x10) ) != 0xCAFEBABE)
		return false;
	
  // sometimes something goes wrong and the frame is corrupted.
  // that's why we triy to detect whether there's a correct
  // jpeg file on every offset
  unsigned int jpgoffset, jpgsize;
  for (int cam = 0; cam < 6; cam++)
  {
    for (int channel = 0; channel < 4; channel++)
    {
      jpegOffsetAndSize(mData, cam, channel, jpgoffset, jpgsize);
      const char* jpg = (const char*)mData+jpgoffset;
      if (jpg+jpgsize > (const char*)mData+frameBytes() || strcmp(jpg+6, "JFIF") != 0)
        return false;
    }
  }

  return true;
}

bool LadybugImage::loadRawImage(int cam, int channel, QImage& img, int scale_pow)
{

	unsigned int jpgadr, jpgsize;
  jpegOffsetAndSize(mData, cam, channel, jpgadr, jpgsize);
	
	if (jpgsize==0)
	{
#ifdef LADY_DEBUG
		printf("jpeg size 0\n");
#endif
		return false;
	}
	
  QByteArray a = QByteArray::fromRawData(reinterpret_cast<const char *>(mData+jpgadr), jpgsize);
  QBuffer b;
  b.setData(a);
  b.open(QIODevice::ReadOnly);

  // using QImageReader directly we can tell the jpeg handler
  // that we want smaller image - we'll avoid down-scaling later
  QImageReader reader(&b, "JPG");
  reader.setQuality(10);
  reader.setScaledSize(QSize(512 >> scale_pow,384 >> scale_pow));
  //img = QImage(256,192, QImage::Format_Indexed8);
  reader.read(&img);

  // TODO: for some reason the scaled image is Format_RGB32
  // instead of Format_Indexed8
  //printf("format: %d\n", img.format());

  return !img.isNull();
}

void LadybugImage::dump(bool dumpData)
{
  printf("--- IMG DUMP ---\n");

  // dump frame header info
  LadybugImageHeader* header = (LadybugImageHeader*) mData;
  LadybugImageInfo* info = (LadybugImageInfo*) (mData+sizeof(LadybugImageHeader));
  printf("data size: %u\n", big2little(header->ulDataSize));
  printf("fingerprint: %X\n", big2little(info->ulFingerprint));
  printf("seq# %u\n", big2little(info->ulSequenceId));

  // dump jpg addresses and sizes
  unsigned int jpgadr, jpgsize;
  for (int cam = 0; cam < 6; cam++)
  {
    printf("Cam %d:\n", cam);
    for (int channel = 0; channel < 4; channel++)
    {
      jpegOffsetAndSize(mData, cam, channel, jpgadr, jpgsize);
      const char* jpg = (const char*)mData+jpgadr;
      bool good = (jpg+jpgsize <= (const char*)mData+frameBytes() && strcmp(jpg+6, "JFIF") == 0);

      printf("- %d | %10x | %10x | %c\n", channel, jpgadr, jpgsize, (good?'O':'X'));

      if (dumpData)
      {
        QFile f(QString("img-%1-%2.jpg").arg(cam).arg(channel));
        f.open(QIODevice::WriteOnly);
        f.write((const char*)(mData+jpgadr), jpgsize);
        f.close();
      }
    }
  }
}
		
QImage LadybugImage::getChannelImage(int cam, int channel, bool rotate, int pow_scale)
{
	QImage img;
  if (!loadRawImage(cam, channel, img, pow_scale))
		return QImage();

  // rotate if asked to do so
  if (rotate)
    return img.transformed(QMatrix(0,1,-1,0,0,img.width()));
  else
    return img;
}
		
QImage LadybugImage::getColorImage(int cam, bool rotate, int pow_scale)
{
	QImage imgR, imgG1, imgG2, imgB;
  if (!loadRawImage(cam, 0, imgR, pow_scale)) return QImage();
  if (!loadRawImage(cam, 1, imgG1, pow_scale)) return QImage();
  //if (!loadRawImage(cam, 2, imgG2, pow_scale)) return QImage();
  if (!loadRawImage(cam, 3, imgB, pow_scale)) return QImage();

  int width = imgR.width();
  int height = imgR.height();
  int origWidth = width, origHeight = height;
  if (rotate)
    qSwap(width, height);
  QImage img(width,height,QImage::Format_RGB32);
  uint* out = (uint*) img.bits();

  int x,y;
  uint color;
  for (y = 0; y < origHeight; y++)
	{
    const QRgb* lineR = (QRgb*) imgR.scanLine(y);
    const QRgb* lineG1 = (QRgb*) imgG1.scanLine(y);
    const QRgb* lineB = (QRgb*) imgB.scanLine(y);
    for (x = 0; x < origWidth; x++)
		{
      color = (0xffu << 24) | ((lineR[x] & 0xff) << 16) | ((lineG1[x] & 0xff) << 8) | (lineB[x] & 0xff);
      if (rotate)
        out[x*width+(origHeight-y-1)] = color;
			else
        out[y*width+x] = color;
		}
	}
			
	return img;
}

unsigned int LadybugImage::frameBytes() const
{
  return mFrameSize;
}

unsigned char* LadybugImage::frameData() const
{
  return mData;
}

unsigned int LadybugImage::time() const
{
  uint secs = big2little( *(unsigned int*)(mData+0x18) );
  uint microsecs = big2little( *(unsigned int*)(mData+0x1C) );
  return  (secs * 1000) + (microsecs / 1000);
}

unsigned int LadybugImage::sequenceId() const
{
  return big2little( *(unsigned int*)(mData+0x20) );
}

void LadybugImage::setAppendedData(QByteArray data)
{
  mAppendedData = data;

  // update internal frame size
  unsigned int* ptr = (unsigned int*)(mData+8);
  *ptr = little2big( mFrameSize + mAppendedData.length() );
}

QByteArray LadybugImage::appendedData() const
{
  return mAppendedData;
}


void LadybugImage::addGpsData(QByteArray data)
{
  setAppendedData(mAppendedData + data);

  // update frame to tell that we've added GPS data
  *(unsigned int*)(mData+0x338) = little2big(mFrameSize); // offset
  *(unsigned int*)(mData+0x33C) = little2big(data.size()); // size
}

void LadybugImage::addPadding()
{
  int frameEnd = ((mFrameSize + mAppendedData.length()) % 512);
  if (frameEnd > 0)
  {
    QByteArray padding(512-frameEnd, '\0');
    setAppendedData(mAppendedData + padding);
  }
}
