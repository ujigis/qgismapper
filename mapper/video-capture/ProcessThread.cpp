#include "ProcessThread.h"

ProcessThread::ProcessThread(GatherThread *gatherThread_):
	gatherThread(gatherThread_)
{
}



ProcessThread::~ProcessThread()
{
}



void ProcessThread::doRun()
{
	AVFrame *frame;
	gettingFirstFrame=true;
	long lastFrameNo=0;
	int resultFrameNo=0;
	
	if (!gatherThread->ensureFullyInitialized())
		return;

	if (!initializeRun()) {
		printf("Couldn't initialize video processing...\n");
		terminateRun();
		return;
	}

	while (!shouldStop()) {
		frame=gatherThread->getFrame();
		if (frame) {
			//duplicate frames, if necessary
			int noCopies, iCopies;

			if (gettingFirstFrame) {
				gettingFirstFrame=false;
				noCopies=gatherThread->getInitialBlankFramesCount();
				lastFrameNo=frame->pts;
			} else {
				noCopies=frame->pts-lastFrameNo;
				lastFrameNo=frame->pts;
			}

			for (iCopies=0; iCopies<noCopies; iCopies++) {
				frame->pts=resultFrameNo++;
				processFrame(frame);
			}
			
			freePicture(frame);
		} else {
			usleep(200);
			if (!gatherThread->isAlive()) {
				printf("Detected dead gatherer, committing harakiri...\n");
				break;
			}
		}
	}
	
	terminateRun();
}
