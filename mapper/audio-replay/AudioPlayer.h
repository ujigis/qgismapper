#ifndef _AUDIOPLAYER_H_
#define _AUDIOPLAYER_H_

#include <QObject>

/**
 * Class representing a replay callback. This class
 * is handed to audio_initialize, and it's purpose is
 * to allow the client applications to get notified about
 * replay events (instead of polling).
**/
class OggReplayCallback : public QObject {
	Q_OBJECT

public:
	virtual ~OggReplayCallback() { }

	/**
	 * This method gets called, when ogg decoding
	 * hits the end of current file. Please note, that the method is
	 * asynchronously called from other than GUI thread.
	**/
	virtual void onOggEnded() { }
};

/**
 * Initialize audio replay libraries
**/
bool audio_initialize(OggReplayCallback *callback);

/**
 * Uninitialize audio replay libraries
**/
bool audio_terminate();

/**
 * Start replaying decoded data
 *
 * Use specified output device. When -1 is passed, it will use default device.
**/
bool audio_start(int outputDevice = -1);

/**
 * Stop replaying decoded data
**/
bool audio_stop();

/**
 * Returns current audio-local time
**/
double audio_getCurrentTime();

/**
 * Open a ogg file
**/
int ogg_openFile(const char *path);

/**
 * Close currently opened file. Also stops decoding of the file.
**/
void ogg_closeFile();

/**
 * Seek the current file to specified time (in seconds)
**/
int ogg_seekToTime(float time);

/**
 * Returns length (in seconds) of current file 
**/
float ogg_getLength();

/**
 * Starts decoding (thread) of current file
**/
void ogg_startDecoding();


/**
 * Audio device information structure
 */
class AudioDevice
{
public:
  int index;
  QString name;
  QString api;
  bool isInput;
  bool isOutput;
};

/**
 * Get List of available devices. Returns valid results after audio_initialize() has been called.
 */
QList<AudioDevice> devices();

/**
 * Find out index of the default output device
 */
int defaultDeviceIndex();

#endif
