#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <portaudio.h>
#include <pthread.h>
#include <vorbis/codec.h>
#include <vorbis/vorbisfile.h>

#ifdef _WIN32
typedef __int16 int16_t;
#endif

#include "../audio-capture/PluginAudioWorker_SamplesBuffer.c"
#include "AudioPlayer.h"

enum {
	SamplesBufferMaxDuration=500,
	OggSamplesPerRead=1024,
};

// Ogg/vorbis stuff
FILE *oggFile=0;
OggVorbis_File ogg;
pthread_spinlock_t ogg_lock;
vorbis_info *vorbisInfo;

int oggSamples;
int oggSampleRate=44100;
int oggChannels;
int oggBitrate;

//PortAudio stuff
PaStream* paStream=0;

SamplesBuffer *samplesBuffer;

pthread_spinlock_t decodingThread_lock;
pthread_t decodingThread;
bool hasDecodingThread=false;
volatile int decodingThread_stop;

OggReplayCallback *replayCallbackClass;

bool audio_initialize(OggReplayCallback *replayCallbackClass_)
{
	pthread_spin_init(&decodingThread_lock, 0);
	pthread_spin_init(&ogg_lock, 0);

	replayCallbackClass=replayCallbackClass_;

	samplesBuffer=sb_createBuffer();
	
	return (Pa_Initialize()==paNoError);
}

bool audio_terminate()
{
	return (Pa_Terminate()==paNoError);
}

static int paCallback(
	const void *inputBuffer,
	void *outputBuffer,
	unsigned long framesPerBuffer,
	const PaStreamCallbackTimeInfo*timeInfo,
	PaStreamCallbackFlags flags,
	void *data
)
{
	//fill the sound card output buffer with data in samples buffer from ogg decoder
	pthread_spin_lock(&decodingThread_lock);
	if (sb_samplesCount(samplesBuffer)==0 && !hasDecodingThread) {
		sb_padWithZeros((int16_t*)outputBuffer, 0, framesPerBuffer*oggChannels-1);
		pthread_spin_unlock(&decodingThread_lock);
		return paContinue;
	}
	pthread_spin_unlock(&decodingThread_lock);

	//silence, if no decoded data are available
	sb_padWithZeros(
		(int16_t*)outputBuffer,
		sb_retrieveData(samplesBuffer, (int16_t*)outputBuffer, framesPerBuffer*oggChannels),
		framesPerBuffer*oggChannels-1
	);

	return paContinue;
}


bool audio_start(int outputDevice /* = -1 */)
{
	PaStreamParameters outStreamSpec;
  outStreamSpec.device = (outputDevice >= 0 ? outputDevice : Pa_GetDefaultOutputDevice());
	
	outStreamSpec.channelCount=2;
	outStreamSpec.sampleFormat=paInt16;
	outStreamSpec.suggestedLatency=0.5;
	outStreamSpec.hostApiSpecificStreamInfo=NULL;

	PaError err=Pa_OpenStream(
		&paStream,
		NULL,
		&outStreamSpec,
		oggSampleRate,
		paFramesPerBufferUnspecified,
		paNoFlag,
		paCallback,
		&ogg
	);

	if (err!=paNoError) {
		printf("error opening PortAudio stream (err no. %d)!\n", err);
		return false;
	}

	err = Pa_StartStream(paStream);
	if (err != paNoError) {
		printf("error starting PortAudio stream (err no. %d)!\n", err);
		return false;
	}

	return true;
}

bool audio_stop()
{
	Pa_CloseStream(paStream);
	paStream=0;

	return true;
}

double audio_getCurrentTime()
{
	return Pa_GetStreamTime(paStream);
}




///OGG decoding part




int ogg_openFile(const char *path)
{
	oggFile=fopen(path, "rb");
	if (!oggFile) return 1;

	int result=ov_open(oggFile, &ogg, NULL, 0);
	if (result<0) {
		fclose(oggFile);
		return 2;
	}

	vorbisInfo=ov_info(&ogg, -1);

	oggSamples=ov_pcm_total(&ogg, -1);
	oggSampleRate=vorbisInfo->rate;
	oggChannels=vorbisInfo->channels;
	oggBitrate=vorbisInfo->bitrate_nominal;

	return 0;
}

void ogg_closeFile()
{
	pthread_spin_lock(&ogg_lock);
	if (!oggFile) {
		pthread_spin_unlock(&ogg_lock);
		return;
	}
	pthread_spin_unlock(&ogg_lock);


	pthread_spin_lock(&decodingThread_lock);
	if (hasDecodingThread==0) {
		pthread_spin_unlock(&decodingThread_lock);
		return;
	}

	decodingThread_stop=1;
	pthread_spin_unlock(&decodingThread_lock);

	pthread_join(decodingThread, NULL);
}

int ogg_seekToTime(float time)
{
	pthread_spin_lock(&ogg_lock);
	int rv=ov_time_seek(&ogg, time);
	pthread_spin_unlock(&ogg_lock);

	return rv;
}

float ogg_getLength()
{
	pthread_spin_lock(&ogg_lock);
	float rv=ov_time_total(&ogg, -1);
	pthread_spin_unlock(&ogg_lock);

	return rv;
}

static void *decodingThreadFct(void *data)
{
	float **oggPcmChannels;
	int oggBitstream;
	long oggDecodedCount, l;
	int16_t *buffer=(int16_t*)malloc(OggSamplesPerRead*oggChannels*sizeof(int16_t));
	int stop=0;

	while (!stop) {
		if (sb_samplesCount(samplesBuffer)<(oggSampleRate*SamplesBufferMaxDuration/1000)) {
			pthread_spin_lock(&ogg_lock);
			oggDecodedCount=ov_read_float(&ogg, &oggPcmChannels, OggSamplesPerRead, &oggBitstream);
			pthread_spin_unlock(&ogg_lock);

			if (oggDecodedCount==0) {
				replayCallbackClass->onOggEnded();
				break;
			}

			if (oggChannels==1) {
				for(l=0; l<oggDecodedCount; l++) {
					buffer[l]=(int16_t)(oggPcmChannels[0][l]*32678.f);
				}
			} else {
				for(l=0; l<oggDecodedCount; l++) {
					buffer[l*2+0]=(int16_t)(oggPcmChannels[0][l]*32678.f);
					buffer[l*2+1]=(int16_t)(oggPcmChannels[1][l]*32678.f);
				}
			}

			sb_appendData(samplesBuffer, (const int16_t*)buffer, oggDecodedCount*oggChannels);
		} else {
#ifndef _WIN32
			// sleeping in microseconds not available on win?
			usleep(SamplesBufferMaxDuration/4);
#endif
		}

		pthread_spin_lock(&decodingThread_lock);
		stop=decodingThread_stop;
		pthread_spin_unlock(&decodingThread_lock);
	}
	
	free(buffer);
	
	pthread_spin_lock(&ogg_lock);
	ov_clear(&ogg);
	oggFile=NULL;
	pthread_spin_unlock(&ogg_lock);

	pthread_spin_lock(&decodingThread_lock);
	hasDecodingThread=false;
	pthread_spin_unlock(&decodingThread_lock);

	pthread_exit(NULL);
	return 0; // we must return something
}

void ogg_startDecoding()
{
	decodingThread_stop=0;
	pthread_create(&decodingThread, NULL, decodingThreadFct, 0);
	hasDecodingThread=true;
}

////////////////////////////////////////////////////////////
//////////// AUDIO BACKEND INFO
////////////////////////////////////////////////////////////


QList<AudioDevice> devices()
{
  QList<AudioDevice> lst;
  int numDevices = Pa_GetDeviceCount();
  if( numDevices < 0 )
    return lst;

  for( int i = 0; i<numDevices; i++ )
  {
    const PaDeviceInfo* deviceInfo = Pa_GetDeviceInfo( i );
    AudioDevice d;
    d.index = i;
    d.name = QString::fromLatin1(deviceInfo->name);
    d.api = QString::fromLatin1(Pa_GetHostApiInfo(deviceInfo->hostApi)->name);
    d.isInput = (deviceInfo->maxInputChannels > 0);
    d.isOutput = (deviceInfo->maxOutputChannels > 0);
    lst.append(d);
  }

  return lst;
}

int defaultDeviceIndex()
{
  return Pa_GetDefaultOutputDevice();
}

