/**
 * @file
 * A simple C implementation of a thread-safe sample buffer.
**/

#ifdef _WIN32
typedef __int16 int16_t;
#endif

enum {
	SamplesBuffer_InitialSize=8192,
};

typedef struct SamplesBuffer {
	pthread_mutex_t lock;
	long dataSize;
	long usedCount;
	int16_t *data;
} SamplesBuffer;

static SamplesBuffer* sb_createBuffer()
{
	SamplesBuffer *buf=(SamplesBuffer*)malloc(sizeof(SamplesBuffer));

	pthread_mutex_init(&buf->lock, NULL);
	buf->dataSize=SamplesBuffer_InitialSize;
	buf->usedCount=0;
	buf->data=(int16_t*)malloc(sizeof(int16_t)*buf->dataSize);
	return buf;
}

static void sb_destroyBuffer(SamplesBuffer* buf)
{
	free(buf->data);
	free(buf);
}

static void sb_lock(SamplesBuffer *buf)
{
	pthread_mutex_lock(&buf->lock);
}

static void sb_unlock(SamplesBuffer *buf)
{
	pthread_mutex_unlock(&buf->lock);
}

static void sb_appendData(SamplesBuffer* buf, const int16_t *data, int frames)
{
	sb_lock(buf);

	if (buf->usedCount+frames>buf->dataSize) {
		buf->data=(int16_t*)realloc(buf->data, (buf->usedCount+frames)*sizeof(int16_t));
		buf->dataSize=buf->usedCount+frames;
	}
	memcpy(buf->data+buf->usedCount, data, frames*sizeof(int16_t));

	buf->usedCount+=frames;

	sb_unlock(buf);
}

static int sb_retrieveData(SamplesBuffer* buf, int16_t *data, int maxFrames)
{
	sb_lock(buf);

	int retrFrames=maxFrames;
	if (retrFrames>buf->usedCount)
		retrFrames=buf->usedCount;

	if (retrFrames!=0) {
		int i;

		memcpy(data, buf->data, retrFrames*sizeof(int16_t));
		
		for (i=0; i<buf->usedCount-retrFrames; i++) {
			buf->data[i]=buf->data[i+retrFrames];
		}
		buf->usedCount-=retrFrames;
	}

	sb_unlock(buf);

	return retrFrames;
}

static void sb_padWithZeros(int16_t *data, int from, int to)
{
	memset(data+from, 0, (to-from+1)*sizeof(int16_t));
}

static long sb_samplesCount(SamplesBuffer *buf) {
	sb_lock(buf);
	long rv=buf->usedCount;
	sb_unlock(buf);

	return rv;
}
