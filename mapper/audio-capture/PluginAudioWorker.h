
#include <QList>
#include <QString>

/**
 * Initialize audio stuff (load libraries etc.)
**/
bool initializeAudio();

/**
 * Uninitialize audio
**/
bool uninitializeAudio();

/**
 * Start audio processing (this makes getRecordedAudioPeak() working).
 *
 * Use specified input device. When -1 is passed, it will use default device.
**/
bool startAudio(int inputDevice = -1);

/**
 * Stop audio processing.
**/
void stopAudio();

/**
 * Start recording to specified file, using default recording device.
**/
bool startRecording(const char *outputFile);

/**
 * Stop ongoing recording.
**/
void stopRecording();

/**
 * Returns audio data peak value, of data that came since the last call of this function.
 * The returned value is scaled to 0-1.
**/
float getCapturedAudioPeak();

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
 * Get List of available devices. Returns valid results after initializeAudio() has been called.
 */
QList<AudioDevice> devices();

/**
 * Find out index of the default input device
 */
int defaultDeviceIndex();
