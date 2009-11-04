#define __STDC_CONSTANT_MACROS
#include <stdint.h>
#include "CompressThread.h"

CompressThread::CompressThread(GatherThread *gatherThread_, const QString &outputFile_, const QString &codec_, int kbitrate_):
	PreviewThread(gatherThread_), outputFile(outputFile_), sCodec(codec_), kbitrate(kbitrate_), img_convert_ctx(0)
{
	whatIsOpened=NOTHING;
	video_outbuf = 0;
	pAvStream=0;
	oc=0;
}



CompressThread::~CompressThread()
{

}


bool CompressThread::openVideo()
{
	if (!initFormat())
		return false;
	if (!initCodec())
		return false;
	
	if (!(fmt->flags & AVFMT_NOFILE)) {
		if (url_fopen(&oc->pb, outputFile.toLocal8Bit().data(), URL_WRONLY) < 0)
			return false;
	}
	whatIsOpened=FILE;
	
	av_write_header(oc);

	return true;
}



bool CompressThread::initFormat()
{
	const char *filename=outputFile.toLocal8Bit().data();

	fmt = guess_format(NULL, filename, NULL);
	if (!fmt)
		fmt = guess_format("mpeg", NULL, NULL);
	if (!fmt)
		return false;

	AVCodec *encoder=avcodec_find_encoder_by_name(sCodec.toLocal8Bit().data());
	if (!encoder) {
		printf("Cannot find encoder %s!\n", sCodec.toLocal8Bit().data());
		return false;
	}

	fmt->video_codec=encoder->id;

#ifdef OLD_FFMPEG
	oc = av_alloc_format_context();
#else
	oc = avformat_alloc_context();
#endif

	if (!oc)
		return false;

	oc->oformat = fmt;
	snprintf(oc->filename, sizeof(oc->filename), "%s", filename);
	
	pAvStream = addVideoStream(oc, fmt->video_codec);
	if (!pAvStream)
		return false;
	
	if (av_set_parameters(oc, NULL) < 0)
		return false;

	dump_format(oc, 0, filename, 1);

	return true;
}



AVStream *CompressThread::addVideoStream(AVFormatContext *oc, CodecID codec_id)
{
	AVCodecContext *c;
	AVStream *st;

	st = av_new_stream(oc, 0);
	if (!st)
		return 0;

	c = st->codec;
	c->codec_id = codec_id;
	c->codec_type = CODEC_TYPE_VIDEO;

	c->bit_rate = kbitrate*1024;
	c->width = gatherThread->getRecordingParameters().width;
	c->height = gatherThread->getRecordingParameters().height;
	c->time_base.den = gatherThread->getRecordingParameters().fps;
	c->time_base.num = 1;
	c->gop_size = 12;

	//use safe pixel format, as gatherThread->getVideoStream()->codec->pix_fmt
	//might not be supported by encoder codec
	c->pix_fmt = PIX_FMT_YUV420P;
	
	if (c->codec_id == CODEC_ID_MPEG2VIDEO)
		c->max_b_frames = 2;
	if (c->codec_id == CODEC_ID_MPEG1VIDEO)
		c->mb_decision=2;
	if(!strcmp(oc->oformat->name, "mp4") || !strcmp(oc->oformat->name, "mov") || !strcmp(oc->oformat->name, "3gp"))
		c->flags |= CODEC_FLAG_GLOBAL_HEADER;

	if (c->codec_id == CODEC_ID_MJPEG)
		c->pix_fmt= PIX_FMT_YUVJ420P;

	return st;
}



bool CompressThread::initCodec()
{
	AVCodecContext *c;
	c = pAvStream->codec;

	codec = avcodec_find_encoder(c->codec_id);
	if (!codec)
		return false;

	if (avcodec_open(c, codec) < 0)
		return false;
	whatIsOpened=CODEC;

	if (!(oc->oformat->flags & AVFMT_RAWPICTURE)) {
		video_outbuf_size = 200000;
		video_outbuf = (uint8_t*)av_malloc(video_outbuf_size);
	}

	tmp_picture = NULL;
	if (c->pix_fmt != gatherThread->getVideoStream()->codec->pix_fmt) {
		tmp_picture = allocPicture(c->pix_fmt, c->width, c->height);
		if (!tmp_picture)
			return false;
	}

	return true;
}



void CompressThread::closeVideo()
{
	if (whatIsOpened==NOTHING)
		return;

	if (oc) {
		if (whatIsOpened>=FILE)
			av_write_trailer(oc);

		if (pAvStream)
			closeCodec(oc, pAvStream);

		unsigned int i;
		for(i = 0; i < oc->nb_streams; i++) {
			av_freep(&oc->streams[i]->codec);
			av_freep(&oc->streams[i]);
		}
		
		if (!(fmt->flags & AVFMT_NOFILE)) {
			if (whatIsOpened>=FILE)
				url_fclose(oc->pb);
		}

		av_free(oc);
	}

	if (tmp_picture!=0) {
		freePicture(tmp_picture);
		tmp_picture=0;
	}
}



void CompressThread::closeCodec(AVFormatContext *, AVStream *st)
{
	if (whatIsOpened>=CODEC)
		avcodec_close(st->codec);

	if (video_outbuf)
		av_free(video_outbuf);
}



bool CompressThread::encodeFrame(AVFrame *picture)
{
	int out_size, ret;
	AVCodecContext *c;
	AVFrame *usedPicture;
	c = pAvStream->codec;
	
	if (c->pix_fmt != gatherThread->getVideoStream()->codec->pix_fmt) {
		if (img_convert_ctx == NULL) {
			img_convert_ctx = sws_getContext(c->width, c->height,
				gatherThread->getVideoStream()->codec->pix_fmt,
				c->width, c->height,
				c->pix_fmt,
				SWS_BICUBIC, NULL, NULL, NULL
			);
			if (img_convert_ctx == NULL) {
				fprintf(stderr, "Cannot initialize the conversion context\n");
				return false;
			}
		}
		
		sws_scale(img_convert_ctx, picture->data, picture->linesize,
			0, c->height, tmp_picture->data, tmp_picture->linesize);
		usedPicture=tmp_picture;
	} else {
		usedPicture=picture;
	}
	
	
	if (oc->oformat->flags & AVFMT_RAWPICTURE) {
		AVPacket pkt;
		av_init_packet(&pkt);
	
		pkt.flags |= PKT_FLAG_KEY;
		pkt.stream_index= pAvStream->index;
		pkt.data= (uint8_t *)usedPicture->data[0];
		pkt.size= sizeof(AVPicture);
	
		ret = av_write_frame(oc, &pkt);
	} else {
		out_size = avcodec_encode_video(c, video_outbuf, video_outbuf_size, usedPicture);

		if (out_size > 0) {
			AVPacket pkt;
			av_init_packet(&pkt);
			if ((uint64_t)(c->coded_frame->pts) != AV_NOPTS_VALUE)
				pkt.pts= av_rescale_q(c->coded_frame->pts, c->time_base, pAvStream->time_base);
			if(c->coded_frame->key_frame)
				pkt.flags |= PKT_FLAG_KEY;
			pkt.stream_index= pAvStream->index;
			pkt.data= video_outbuf;
			pkt.size= out_size;
	
			ret = av_write_frame(oc, &pkt);
		} else {
			ret = 0;
		}
	}
	if (ret != 0) {
		fprintf(stderr, "Error while writing video frame\n");
		return 1;
	}
	
	return true;
}

