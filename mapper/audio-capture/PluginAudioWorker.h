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
**/
bool startAudio();

/**
 * Stop audio processing.
**/
void stopAudio();

/**
 * Start recording to specified file, using default recording device.
**/
bool startRecording(const char *outputFile);

/**
 * Stop ongoing recording/
**/
void stopRecording();

/**
 * Returns audio data peak value, of data that came since the last call of this function.
 * The returned value is scaled to 0-1.
**/
float getCapturedAudioPeak();
