#ifndef _COMPRESSTHREAD_H_
#define _COMPRESSTHREAD_H_

#include "PluginInternals.h"
#include "GatherThread.h"
#include "ProcessThread.h"
#include "PreviewThread.h"

class CompressThread: public PreviewThread {
public:
	/**
	 * @param outputFile_ File to be written to.
	 * @param codec_ Codec to be used.
	 * @param kbitrate_ Bitrate (in kbits) of the saved video stream.
	**/
	CompressThread(GatherThread *gatherThread_, const QString &outputFile_, const QString &codec_, int kbitrate_);

	virtual ~CompressThread();

protected:
	virtual bool initializeRun()  { return PreviewThread::initializeRun() && openVideo(); }
	virtual void terminateRun() { PreviewThread::terminateRun(); closeVideo(); }
	virtual void processFrame(AVFrame *picture) { encodeFrame(picture); PreviewThread::processFrame(picture); }

private:
	bool openVideo();
	bool initFormat();
	AVStream *addVideoStream(AVFormatContext *oc, CodecID codec_id);
	bool initCodec();

	void closeVideo();
	void closeCodec(AVFormatContext *, AVStream *st);

	bool encodeFrame(AVFrame *picture);
private:
	QString outputFile;
	QString sCodec;
	int kbitrate;

	AVOutputFormat *fmt;
	AVFormatContext *oc;
	AVStream *pAvStream;
	uint8_t *video_outbuf;
	int video_outbuf_size;

	AVCodec *codec;
	AVFrame *tmp_picture;

	SwsContext *img_convert_ctx;

	enum {
		NOTHING,
		CODEC,
		FILE
	} whatIsOpened;
};

#endif //_COMPRESSTHREAD_H_
