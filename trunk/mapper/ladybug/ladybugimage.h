/******************************************************************************
 *   Copyright (c) 2009 Martin Dobias
 *
 *   This program is free software; you can redistribute it and/or modify
 *   it under the terms of the GNU General Public License as published by
 *   the Free Software Foundation; either version 2 of the License, or
 *   (at your option) any later version.
 ******************************************************************************/

#ifndef LADYBUGIMAGE_H
#define LADYBUGIMAGE_H

class QImage;

class LadybugImage
{
public:
  //! construct invalid image
  LadybugImage();

  //! construct a valid image, takes ownership if ownData == TRUE
  LadybugImage(unsigned char* data, unsigned int size, bool ownData = true);

  //! copy constructor - makes deep copy of the data
  LadybugImage(const LadybugImage& other);

  ~LadybugImage();

  //! initialize image with new data (deletes previous data is has ownership)
  void setData(unsigned char* data, unsigned int size, bool ownData = true);

  //! check whether the frame is correct
  bool isValid() const;

  //! load raw image from one channel of a camera, scale it and optionally rotate
  QImage getChannelImage(int cam, int channel, bool rotate, int pow_scale);

  //! load raw images from camera's channels and mix them, scale them and optionally rotate
  QImage getColorImage(int cam, bool rotate, int pow_scale);

	//! load raw image from JPEG compressed data
  bool loadRawImage(int cam, int channel, QImage& img, int pow_scale);
	
	//! return length of the frame in bytes
	unsigned int frameBytes() const;
	
	//! return pointer to frame data
	unsigned char* frameData() const;

  //! dump image information to standard output
  void dump(bool dumpData=false);

  //! time of the frame in miliseconds (counted from 0 when camera is turned on)
  unsigned int time() const;

  //! sequence id of the frame (counted from 0 when camera is turned on)
  unsigned int sequenceId() const;

protected:

  unsigned char* mData;
  unsigned int mSize;
  bool mOwnData;
};

#endif
