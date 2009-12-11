#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <portaudio.h>
#include <pthread.h>
#include <assert.h>
#include <vorbis/vorbisenc.h>

#include "PluginAudioWorker.h"
#include "PluginAudioWorker_SamplesBuffer.c"


enum {
	RecordingNoOfChannels=2,
	DefaultSampleRate=44100,
};

typedef struct RecordingParams {
	FILE *outputFile;

	vorbis_info vi;
	vorbis_dsp_state vd;
	vorbis_block vb;
	vorbis_comment vc;

	ogg_stream_state os;
	ogg_page og;
	ogg_packet op;
} RecordingParams;



pthread_t recordingThread=0;
pthread_mutex_t threadRunMutex=PTHREAD_MUTEX_INITIALIZER;
volatile int threadRunStop;

//this ain't thread-protected, though it's used in multithread environment,
//however we don't mind occasional glitches... :)
float audioPeakValue=0;

///audio stream handle
static PaStream* audioStream;

///buffer containing captured audio data
static SamplesBuffer *recBuffer;

///lock around recBuffer to ensure that it's allocated always in consistent state
static pthread_spinlock_t recBufferLock;




////////////////////////////////////////////////////////////
//////////// AUDIO (DE)INITIALIZADION
////////////////////////////////////////////////////////////

bool initializeAudio()
{
	PaError err=Pa_Initialize();

#ifdef MAKETEST
	printf("Devs: %d\ndefInp: %d\n", Pa_GetDeviceCount(), Pa_GetDefaultInputDevice());

	const PaDeviceInfo*di=Pa_GetDeviceInfo(Pa_GetDefaultInputDevice());
	printf("defNfo: %s\ndefHostApi: %d\n", di->name, di->hostApi);
#endif

	pthread_spin_init(&recBufferLock, 0);
	recBuffer=0;
	audioStream=0;
	
	return (err==paNoError);
}

bool uninitializeAudio()
{
	pthread_spin_destroy(&recBufferLock);

	return (Pa_Terminate()==paNoError);
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
  return Pa_GetDefaultInputDevice();
}


////////////////////////////////////////////////////////////
//////////// AUDIO CAPTURE
////////////////////////////////////////////////////////////



static int paCallback(
	const void *inputBuffer,
	void */*outputBuffer*/,
	unsigned long framesPerBuffer,
	const PaStreamCallbackTimeInfo*/*timeInfo*/,
	PaStreamCallbackFlags /*flags*/,
	void *
)
{
#ifdef MAKETEST
	putc('.', stdout);fflush(stdout);
#endif
	pthread_spin_lock(&recBufferLock);
	if (recBuffer!=0)
		sb_appendData(recBuffer, (const int16_t*)inputBuffer, framesPerBuffer*RecordingNoOfChannels);
	pthread_spin_unlock(&recBufferLock);

	unsigned int i;
	int16_t maxVal=0;
	const int16_t *buf=(const int16_t*)inputBuffer;

	for (i=0; i<framesPerBuffer*RecordingNoOfChannels; i++) {
		if (abs(*buf)>maxVal)
			maxVal=abs(*buf);
		buf++;
	}
	if ((maxVal/32678.f)>audioPeakValue)
		audioPeakValue=maxVal/32678.f;
	return paContinue;
}



bool startAudio(int inputDevice /* = -1 */)
{
	PaStreamParameters inStreamSpec;
  inStreamSpec.device = (inputDevice >= 0 ? inputDevice : Pa_GetDefaultInputDevice());

  const PaDeviceInfo* info = Pa_GetDeviceInfo(inStreamSpec.device);

  // set parameters
	inStreamSpec.channelCount=RecordingNoOfChannels;
	inStreamSpec.sampleFormat=paInt16;
  // use high input latency... when setting low input latency the recording tends to hang
  // after few seconds (no idea what's the reason)
  inStreamSpec.suggestedLatency=info->defaultHighInputLatency;
	inStreamSpec.hostApiSpecificStreamInfo=NULL;

	PaError err=Pa_OpenStream(
		&audioStream,
		&inStreamSpec,
    NULL,
    DefaultSampleRate,
		paFramesPerBufferUnspecified,
		paNoFlag,
		paCallback,
		0
	);

	if (err!=paNoError) {
		printf("error opening stream!\n");
		return false;
	}

  Pa_StartStream(audioStream);

	return true;
}

void stopAudio()
{
	//Pa_StopStream(audioStream);
	Pa_CloseStream(audioStream); //calls pa_abort automatically
}










////////////////////////////////////////////////////////////
//////////// AUDIO COMPRESSION
////////////////////////////////////////////////////////////

void ogg_flushall(RecordingParams *rp)
{
	while(1) {
		int result=ogg_stream_flush(&rp->os,&rp->og);
		if(result==0)
			break;
		fwrite(rp->og.header,1,rp->og.header_len,rp->outputFile);
		fwrite(rp->og.body,1,rp->og.body_len,rp->outputFile);
	}
}



static void *recordingThreadFct(void *data)
{
	enum {
		bufInCount=1024,
		bufInSize=2*bufInCount,
	};
	
	short int bufIn[bufInSize];
	char *bufInBytes=(char*)bufIn;
	ogg_packet op;
	RecordingParams *rp=(RecordingParams*)data;
	int l;

	while (1) {
		sb_lock(recBuffer);
		if (recBuffer->usedCount>=bufInSize) {
			//buffer contains enough data, let's encode it
			sb_unlock(recBuffer);

			sb_retrieveData(recBuffer, bufIn, bufInSize);

			//convert PCM to OGG library compatible format
			float **buffer = vorbis_analysis_buffer(&rp->vd, bufInCount);
			if (rp->vi.channels==1) {
				for(l=0; l<bufInCount; l++) {
					buffer[0][l]=((bufInBytes[l*2+1]<<8)|(0x00ff&(int)bufInBytes[l*2]))/32768.f;
				}
			} else {
				for(l=0; l<bufInCount; l++) {
					buffer[0][l]=((bufInBytes[l*4+1]<<8)|(0x00ff&(int)bufInBytes[l*4]))/32768.f;
					buffer[1][l]=((bufInBytes[l*4+3]<<8)|(0x00ff&(int)bufInBytes[l*4+2]))/32768.f;
				}
			}
			
			//encode and write out
			vorbis_analysis_wrote(&rp->vd, bufInCount);

			while(vorbis_analysis_blockout(&rp->vd, &rp->vb) == 1) {
				vorbis_analysis(&rp->vb, NULL);
				vorbis_bitrate_addblock(&rp->vb);

				while(vorbis_bitrate_flushpacket(&rp->vd, &op)) {
					ogg_stream_packetin(&rp->os,&op);
					ogg_flushall(rp);
				}
			}
		} else {
			//not much in the buffer, wait for a while to get new data
			sb_unlock(recBuffer);
			usleep(400);
		}
		
		pthread_mutex_lock(&threadRunMutex);
		if (threadRunStop) {
			pthread_mutex_unlock(&threadRunMutex);
			break;
		}
		pthread_mutex_unlock(&threadRunMutex);
	}

	//close encoder and output file
	vorbis_analysis_wrote(&rp->vd, 0);
	ogg_flushall(rp);

	vorbis_block_clear(&rp->vb);
	vorbis_dsp_clear(&rp->vd);
	vorbis_info_clear(&rp->vi);

	fclose(rp->outputFile);

	//empty output buffer
	pthread_spin_lock(&recBufferLock);
	sb_destroyBuffer(recBuffer);
	recBuffer=0;
	pthread_spin_unlock(&recBufferLock);

	free(rp);

	pthread_exit(NULL);
}



bool startRecording(const char *outputFile)
{
	assert(recordingThread==0);

	//initialize output file
	RecordingParams *rp=(RecordingParams*)malloc(sizeof(RecordingParams));
	rp->outputFile=fopen(outputFile, "wb");
	if (rp->outputFile==NULL) {
		free(rp);
		return false;
	}

	//initialize vorbis encoder
	vorbis_info_init(&rp->vi);
	vorbis_encode_init_vbr(&rp->vi, RecordingNoOfChannels, DefaultSampleRate, .5);
	vorbis_comment_init(&rp->vc);
	vorbis_comment_add_tag(&rp->vc,(char*)"ENCODER",(char*)"QGis-mapper ogg encoder");
	vorbis_analysis_init(&rp->vd, &rp->vi);
	vorbis_block_init(&rp->vd, &rp->vb);

	//initialize ogg output stream
	srand(time(NULL));
	ogg_stream_init(&rp->os,rand());
	{
		ogg_packet header;
		ogg_packet header_comm;
		ogg_packet header_code;
		
		vorbis_analysis_headerout(&rp->vd,&rp->vc,&header,&header_comm,&header_code);
		ogg_stream_packetin(&rp->os,&header);
		ogg_stream_packetin(&rp->os,&header_comm);
		ogg_stream_packetin(&rp->os,&header_code);
		
		ogg_flushall(rp);
	}

	//initialize audio buffer
	pthread_spin_lock(&recBufferLock);
	recBuffer=sb_createBuffer();
	pthread_spin_unlock(&recBufferLock);
	
	threadRunStop=0;
	pthread_create(&recordingThread, NULL, recordingThreadFct, rp);

	return true;
}

void stopRecording()
{
	assert(recordingThread!=0);

	pthread_mutex_lock(&threadRunMutex);
	threadRunStop=1;
	pthread_mutex_unlock(&threadRunMutex);

	pthread_join(recordingThread, NULL);

	recordingThread=0;
}

float getCapturedAudioPeak()
{
	float rv=audioPeakValue;
	audioPeakValue=0;

	return rv;
}


#ifdef MAKETEST
//gcc -DMAKETEST PluginAudioWorker.c -l portaudio -l pthread -l vorbis -l ogg -l vorbisfile -l vorbisenc && ./a.out

void testBuffer()
{/*
	printf("SamplesBuffer\n");
	printf("\tcreate\n");
	SamplesBuffer*b= sb_createBuffer();
	
	printf("\tappend(abcd\\0\\0)\n");
	sb_appendData(b, "abcd\0\0", 3);
	char buf[10];
	printf("\tretrieve\n");
	sb_retrieveData(b, buf, 3);
	printf("\t\t%s\n", buf);

	printf("\tappend(abcd);append(abcd\\0\\0)\n");
	sb_appendData(b, "abcd", 2);
	sb_appendData(b, "abcd\0\0", 3);
	printf("\tretrieve(3);retrieve(2)\n");
	sb_retrieveData(b, buf, 3);buf[6]=0;
	printf("\t\t%s\n", buf);
	sb_retrieveData(b, buf, 2);
	printf("\t\t%s\n", buf);

	printf("\tdestroy\n");
	sb_destroyBuffer(b);
*/}


int main()
{
	printf("INIT: %d\n", initializeAudio());

	//testBuffer();

	startAudio();
	startRecording("test.ogg");
	sleep(5);
	stopRecording();
	stopAudio();

	printf("DEINIT: %d\n", uninitializeAudio());

	return 0;
}
#endif
