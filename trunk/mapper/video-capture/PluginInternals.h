#ifndef _PLUGININTERNALS_H_
#define _PLUGININTERNALS_H_

#include "timeval.h"

#include "PluginVideoWorker.h"

/**
 * Allocate a ffmpeg picture (and also required bitmap memory)
**/
AVFrame *allocPicture(int pix_fmt, int width, int height);

/**
 * Free a ffmpeg picture previously allocated by allocPicture.
**/
void freePicture(AVFrame *f);

/**
 * Substract two timevals and return the result in result. Returns
 * whether x < y.
**/
int timeval_subtract(timeval *result, timeval *x, timeval *y);

/**
 * Returns difference between specified timevels in seconds.
**/
double operator-(timeval x, timeval y);

#if ((LIBAVCODEC_VERSION_INT>>16)&0xff)<52
  #define OLD_FFMPEG
#endif

#endif //_PLUGININTERNALS_H_
