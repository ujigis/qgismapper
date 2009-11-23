/******************************************************************************
 *   Copyright (c) 2009 Martin Dobias
 *
 *   This program is free software; you can redistribute it and/or modify
 *   it under the terms of the GNU General Public License as published by
 *   the Free Software Foundation; either version 2 of the License, or
 *   (at your option) any later version.
 ******************************************************************************/

#include <stdio.h>
#include <inttypes.h>   // kvoli PRIx64

#ifndef WIN32
#include <dc1394/dc1394.h>
#else
typedef void dc1394_t;
typedef void dc1394camera_t;
#endif

#include <QImage>
#include <QMetaType>
#include <QDir>

#include "ladybug.h"
#include "ladybugimage.h"
#include "ladybugthread.h"

#undef LADY_DEBUG

#ifndef WIN32
#include <arpa/inet.h>
#else
#include <winsock.h>
#endif


#ifndef WIN32
void get_serial_number(dc1394camera_t *camera)
{
	uint32_t serial;
	if (dc1394_get_control_register(camera, 0x1f20, &serial) != DC1394_SUCCESS)
	{
		printf("Couldn't get camera's serial number.\n");
		return;
	}
	
	printf("Serial number: %u\n", serial);
}

void get_firmware_version(dc1394camera_t *camera)
{
	uint32_t fw, fw_time;
	if (dc1394_get_control_register(camera, 0x1f60, &fw) != DC1394_SUCCESS
		|| dc1394_get_control_register(camera, 0x1f64, &fw_time) != DC1394_SUCCESS)
	{
		printf("Couldn't get Firmware info.\n");
		return;
	}
	int major = (fw >> 24);
	int minor = (fw >> 16)&0xff;
	int type = (fw >> 12)&0xf;
	int rev = fw & 0xfff;
	printf("firmware: %d.%d.%d.%d\n", major, minor, type, rev);
	
	char buf[80];
	struct tm  *ts;
 
	/* Format and print the time, "ddd yyyy-mm-dd hh:mm:ss zzz" */
        time_t t = fw_time;
        ts = localtime(&t);
	strftime(buf, sizeof(buf), "%a %Y-%m-%d %H:%M:%S %Z", ts);
        printf("firmware build: %s\n", buf);
}

bool get_jpeg_compression(dc1394camera_t* camera, bool& auto_control, int& jpg_quality, int& buffer_usage)
{
  // see TAN2008014 - Control and Status Registers Unique to Ladybug2 and Ladybug3 cameras

  uint32_t rate, usage;
  if (dc1394_get_control_register(camera, 0x1e80, &rate) != DC1394_SUCCESS
      || dc1394_get_control_register(camera, 0x1e84, &usage) != DC1394_SUCCESS)
    return false;

  // check whether theses features are available (should be for ladybug2)
  if (!(rate >> 31) || !(usage >> 31))
    return false;

  // set output values
  auto_control = (rate >> 24) & 1;
  jpg_quality = rate & 0xff;
  buffer_usage = usage & 0xff;
  return true;
}

bool set_jpeg_compression(dc1394camera_t* camera, bool auto_control, int jpg_quality, int buffer_usage)
{
  uint32_t control = (auto_control ? (1 << 24) : 0);
  uint32_t quality = (jpg_quality >= 0 && jpg_quality <= 100 ? jpg_quality : 0);
  uint32_t rate = 0x80000000 | control | quality;
  if (dc1394_set_control_register(camera, 0x1e80, rate) != DC1394_SUCCESS)
    return false;

  uint32_t usage = 0x80000000 | (buffer_usage < 128 && buffer_usage >= 0 ? buffer_usage : 0);
  if (dc1394_set_control_register(camera, 0x1e84, usage) != DC1394_SUCCESS)
    return false;

  return true;
}

void get_camera_calibration(dc1394camera_t *camera)
{
	// this returns about 200kb of data (and it takes some seconds to retrieve it)

	dc1394error_t err;
	uint32_t val;
	uint32_t reg = 0x1000;
	
	FILE* fw = fopen("calibration.txt","w");
	while ( (err=dc1394_get_adv_control_register(camera, reg, &val)) == DC1394_SUCCESS)
	{
		val = htonl(val); // big endian to little endian
		fwrite(&val, 4,1,fw);
		reg+=4;
	}
	fclose(fw);
}

int init_format7(dc1394camera_t *camera, bool compress)
{
	dc1394error_t err;
	dc1394video_mode_t video_mode;
	dc1394operation_mode_t opmode;

	uint32_t hsize, vsize;
	uint32_t hunit, vunit;
	uint32_t unit_bytes, max_bytes;
	uint32_t rec_size;

	int nImageWidth, nImageHeight;
	int nLeftOffset  = 0;
	int nTopOffset   = 0;

	if (compress)
	{
		nImageWidth  = 512;
    nImageHeight = 4096; //2000; //9216; // staci aj menej, hlavne aby sa tam zmestili obrazky
		video_mode = DC1394_VIDEO_MODE_FORMAT7_7;
	}
	else
	{
		nImageWidth  = 1024;
		nImageHeight = 4608;
		video_mode = DC1394_VIDEO_MODE_FORMAT7_0;
	}

	dc1394_camera_print_info( camera, stdout );
	
	printf("=======================\n");
	
	// initialize this camera
	err = dc1394_camera_reset( camera );
	DC1394_ERR_RTN(err,"Could not reset camera");

	// testy na format7
	err=dc1394_format7_get_max_image_size(camera, video_mode, &hsize, &vsize);
	DC1394_ERR_RTN(err,"Could not get max image size");
	printf("format7 max img size: %d x %d\n", hsize, vsize);

	err=dc1394_format7_get_unit_size(camera, video_mode, &hunit, &vunit);
	DC1394_ERR_RTN(err,"Could not get unit size");
	printf("format7 unit size: %d x %d\n", hunit, vunit);
	
	err=dc1394_format7_get_packet_parameters(camera, video_mode, &unit_bytes, &max_bytes);
	DC1394_ERR_RTN(err,"Could not get packet params");
	printf("format7 packet unit %d max %d\n", unit_bytes, max_bytes);

	err=dc1394_format7_get_recommended_packet_size(camera, video_mode, &rec_size);
	DC1394_ERR_RTN(err,"Could not get recommended packet size");
	printf("format7 recommended packet size %d\n", rec_size);
	
	get_serial_number(camera);
	get_firmware_version(camera);

	printf("=======================\n");

	err = dc1394_video_get_operation_mode( camera, &opmode );
	DC1394_ERR_RTN(err,"Could not get operation mode");
	printf("get operation mode: %u\n", opmode);

	opmode = DC1394_OPERATION_MODE_1394B;
	printf("setting operation mode...\n");
	err = dc1394_video_set_operation_mode( camera, opmode );
	DC1394_ERR_RTN(err,"Could not SET operation mode");

	err = dc1394_video_get_operation_mode( camera, &opmode );
	DC1394_ERR_RTN(err,"Could not get operation mode");
	printf("get operation mode: %u\n", opmode);


	err = dc1394_video_set_iso_speed( camera, DC1394_ISO_SPEED_400 ); //400 );
	DC1394_ERR_RTN(err,"Could not set iso speed");

	unsigned int bandwidth_usage;
	err=dc1394_video_get_bandwidth_usage (camera, &bandwidth_usage);
	DC1394_ERR_RTN(err,"Could not get bandwidth usage");
	printf("bandwidth usage: %u\n", bandwidth_usage);

	err = dc1394_format7_set_roi( camera,
					video_mode,
					DC1394_COLOR_CODING_MONO8,
					4096, // bytes per packet
					nLeftOffset, 
					nTopOffset,
					nImageWidth,
					nImageHeight );
	DC1394_ERR_RTN(err,"Could not set ROI");

	// NOTE: for most PGR cameras, format 7, mode 0 is ROI mode.  However, this should
	// be verified by checking the camera technical manual
	err = dc1394_video_set_mode( camera, video_mode );
	DC1394_ERR_RTN(err,"Could not set video mode");

  uint64_t bytes;
  err=dc1394_format7_get_total_bytes(camera, video_mode, &bytes);
  DC1394_ERR_RTN(err,"Could not get total bytes");
  printf("total bytes: %llu\n", bytes);

	return 0;
}



int init_capture(dc1394camera_t *camera, bool compress)
{
	dc1394error_t err;

	printf("init: %d\n", init_format7(camera, compress));

  // default: set jpeg compression: auto control + 80% buffer usage
  // (otherwise it uses fixed high compression rate -> low image quality)
  if (!set_jpeg_compression(camera, true, 0, 0x66))
  {
    printf("Couldn't set up JPEG compression settings!\n");
    return 1;
  }


	err=dc1394_video_set_transmission(camera, DC1394_ON);
	DC1394_ERR_RTN(err,"Could not start transmission");

  uint32 num_dma_buffers = 10; // number of buffers shouldn't be high, might cause problems
  err=dc1394_capture_setup(camera, num_dma_buffers, DC1394_CAPTURE_FLAGS_DEFAULT);
	if (err != DC1394_SUCCESS)
	{
		// if the previous communication wasn't correct, reset the bus and start again!
		// (it's rude but we really would like to talk to ladybug)
		printf("Couldn't setup capture, resetting bus!\n");

		err= dc1394_reset_bus(camera);
		DC1394_ERR_RTN(err,"Could not reset bus");

		printf("init: %d\n", init_format7(camera, compress));
	
		err=dc1394_video_set_transmission(camera, DC1394_ON);
		DC1394_ERR_RTN(err,"Could not start transmission");

    err=dc1394_capture_setup(camera, num_dma_buffers, DC1394_CAPTURE_FLAGS_DEFAULT);
		DC1394_ERR_RTN(err,"Could not setup capture (2)");
	}

	return 0;
}

int exit_capture(dc1394camera_t *camera)
{
	dc1394error_t err;

	err=dc1394_video_set_transmission(camera, DC1394_OFF);
	DC1394_ERR_RTN(err,"Could not stop transmission");
	
	err=dc1394_capture_stop(camera);
	DC1394_ERR_RTN(err,"Could not stop capture");

	return 0;
}

int inspect_camera(dc1394camera_t *camera)
{
	dc1394error_t err;
	dc1394video_modes_t video_modes;
	dc1394video_mode_t video_mode;
	dc1394framerates_t framerates;
	unsigned int i;

	// get supported modes!
	err = dc1394_video_get_supported_modes(camera, &video_modes);
	printf("video modes: %d\n", video_modes.num);
	DC1394_ERR_RTN(err,"Could not get modes");
	for (i = 0; i < video_modes.num; i++)
	{
		printf("- %d\n", video_modes.modes[i]);
	}
	// ladybug2 podporuje:
	// - DC1394_VIDEO_MODE_1024x768_MONO8
	// - DC1394_VIDEO_MODE_FORMAT7_0, 1, 6, 7
	video_mode = DC1394_VIDEO_MODE_1024x768_MONO8;

	// get supported framerates!
	err = dc1394_video_get_supported_framerates(camera, video_mode, &framerates);
	DC1394_ERR_RTN(err,"Could not get framerates");
	printf("framerates: %d\n", framerates.num);
	for (i = 0; i < framerates.num; i++)
	{
		printf("- %d\n", framerates.framerates[i]);
	}
	// ladybug2 podporuje: DC1394_FRAMERATE_1_875, _3_75, _7_5, _15, _30  (mod 1024x768 mono8)
	// (format7 nepodporuje frame rates)
	
	return 0;
}
#endif

////////////

class LadybugPrivate
{

public:
  LadybugPrivate(Ladybug& cam) : thread(cam) {}
	dc1394_t * dc;
	dc1394camera_t *camera;
        uint32 serialHead;
  LadybugThread thread;
  QString errorMsg;
  bool active;
  LadybugCounter counter;
  QMutex mutexCamera;
  double lon,lat;
};

Ladybug::Ladybug()
{
  qRegisterMetaType<LadybugFrame>("LadybugFrame");

  d = new LadybugPrivate(*this);
	d->serialHead = 0;
  d->active = false;
  d->lon = d->lat = 0;
}

Ladybug::~Ladybug()
{
  if (d->active)
  {
    // try to exit gracefully
    exit();
  }

	delete d;
}


bool Ladybug::init()
{
  if (d->active)
  {
    d->errorMsg = "Already initialized.";
    return false;
  }

#ifndef WIN32
  d->dc = dc1394_new();
  if (!d->dc)
  {
    d->errorMsg = "Failed to initialize firewire.";
		return false;
	}

	dc1394camera_list_t * list;
  if (dc1394_camera_enumerate(d->dc, &list) != DC1394_SUCCESS)
  {
    dc1394_free(d->dc);
    d->errorMsg = "Could not enumerate cameras.";
    return false;
  }

  //printf("cameras: %d\n", list->num);
	if (list->num == 0)
  {
    dc1394_free(d->dc);
    d->errorMsg = "No cameras found.";
    return false;
  }

  // get camera! (use the first one)
	d->camera = dc1394_camera_new(d->dc, list->ids[0].guid);
	if (!d->camera)
	{
		printf("camera_new error\n");
    dc1394_free(d->dc);
    d->errorMsg = "Couldn't access camera.";
    return false;
	}
	
  // initialize capture, in compressed mode
  if (init_capture(d->camera, true) != 0)
  {
    dc1394_camera_free(d->camera);
    dc1394_free(d->dc);
    d->errorMsg = "Couldn't init capture.";
    return false;
  }
	
  // make the connection queued
  connect(&d->thread, SIGNAL(capturedFrame(LadybugFrame)),
          this, SLOT(receivedFrame(LadybugFrame)), Qt::QueuedConnection);

  // start the capture thread
  d->thread.setCamera(d->camera);
  d->thread.start();

  d->active = true;

  return true;
#else
  return false;
#endif
}


bool Ladybug::exit()
{
  if (!d->active)
    return false;

#ifndef WIN32
    // make sure we're not recording
    if (d->thread.isRecording())
      d->thread.stopRecording();

    if (d->thread.isRunning())
    {
        printf("stopping thread...\n");
        d->thread.stopCapture();
        bool res = d->thread.wait(3000); // wait 3 seconds
        if (res)
        {
          printf("done stopping.\n");
        }
        else
        {
          d->thread.terminate();
          printf("not responding -> had to terminate it :-(\n");
        }
    }

	exit_capture(d->camera);

	
	dc1394_camera_free(d->camera);
	dc1394_free(d->dc);

  d->active = false;
	
  return true;
#else
  return false;
#endif
}


QByteArray Ladybug::fetchCalibration()
{
  if (!d->active)
    return QByteArray();

  QByteArray calibr;

  QString ladybugDir = ".ladybug";
  QString calibrationPath = QString("%1/%2/calibration.%3").arg(QDir::homePath()).arg(ladybugDir).arg(d->serialHead);

  // first check whether we don't have already the calibration saved in a file
  if (QFile::exists(calibrationPath))
  {
    QFile f(calibrationPath);
    if (f.open(QIODevice::ReadOnly))
    {
      calibr = f.readAll();
      f.close();
      printf("using cached calibration\n");
      return calibr;
    }
  }

#ifndef WIN32
	dc1394error_t err;
	uint32_t val[8];
	int i, reg_cnt = 8;
	uint32_t reg = 0x1000;

  printf("fetching calibration\n");
	
	// load several registers at once. beware - trying to read many at once (e.g. > 14) fails
	while ( (err=dc1394_get_adv_control_registers(d->camera, reg, val,reg_cnt)) == DC1394_SUCCESS)
	{
		for (i =0; i < reg_cnt; i++)
			val[i] = htonl(val[i]); // big endian to little endian
		
		if (calibr.isEmpty())
			calibr = QByteArray((const char*) &val, 4*reg_cnt); // this is to avoid shallow copy that would result in incorrect data
		else
			calibr += QByteArray::fromRawData((const char*) &val, 4*reg_cnt);

		reg+=4 * reg_cnt;
	}
	
	// check whether we haven't read also some 0xff values at the end. if so, remove them!
	int ff = calibr.indexOf(0xff);
	if (ff != -1) calibr.truncate(ff);

  printf("fetch of calibration done\n");

  // try to save the calibration for next time (so we don't have to fetch it every time)
  QDir(QDir::homePath()).mkpath(ladybugDir);
  QFile f(calibrationPath);
  if (f.open(QIODevice::WriteOnly))
  {
    f.write(calibr);
    f.close();
    printf("calibration cached\n");
  }
	
	return calibr;
#else
  return QByteArray();
#endif
}
	
uint32 Ladybug::serialNumBase()
{
  if (!d->active)
    return 0;

#ifndef WIN32
  uint32_t serial;
	if (dc1394_get_control_register(d->camera, 0x1f20, &serial) != DC1394_SUCCESS)
		return 0;
	return serial;
#else
  return 0;
#endif
}

uint32 Ladybug::serialNumHead()
{
  if (!d->active)
    return 0;

  return d->serialHead;
}


void Ladybug::receivedFrame(LadybugFrame frame)
{
    emit capturedFrame(frame);
}


void Ladybug::setPreviewSettings(int camMask, bool color, int interval)
{
  if (!d->active)
    return;

  d->thread.setPreviewSettings(camMask, color, interval);
}

void Ladybug::previewSettings(int& camMask, bool& color, int& interval)
{
  if (!d->active)
    return;

  d->thread.previewSettings(camMask, color, interval);
}


void Ladybug::startRecording(QString streamName)
{
  if (!d->active)
    return;

  d->thread.startRecording(streamName);
}

void Ladybug::stopRecording()
{
  if (!d->active)
    return;

  d->thread.stopRecording();
}

bool Ladybug::isRecording()
{
  if (!d->active)
    return false;

  return d->thread.isRecording();
}

void Ladybug::setSerialHead(uint32 serial)
{
  if (!d->active)
    return;

  d->serialHead = serial;
}

QString Ladybug::errorMessage()
{
  return d->errorMsg;
}

bool Ladybug::isActive() const
{
  return d->active;
}

bool Ladybug::setJpegCompression(bool autoControl, int jpgQuality, int bufferUsage)
{
  return set_jpeg_compression(d->camera, autoControl, jpgQuality, bufferUsage);
}

bool Ladybug::jpegCompression(bool& autoControl, int& jpgQuality, int& bufferUsage)
{
  return get_jpeg_compression(d->camera, autoControl, jpgQuality, bufferUsage);
}

LadybugCounter& Ladybug::counter()
{
  return d->counter;
}

void Ladybug::setCurrentGpsInfo(LadybugGpsInfo& gpsInfo)
{
  d->thread.setCurrentGpsInfo(gpsInfo);
}
