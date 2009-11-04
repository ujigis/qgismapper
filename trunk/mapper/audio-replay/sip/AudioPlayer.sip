%Module AudioPlayer 0

%Import QtCore/QtCoremod.sip
%Import QtGui/QtGuimod.sip

class OggReplayCallback : QObject {

%TypeHeaderCode
#include <AudioPlayer.h>
%End

public:
	virtual ~OggReplayCallback();

	virtual void onOggEnded();
};

%UnitCode
#include <AudioPlayer.h>
%End

bool audio_initialize(OggReplayCallback *callback);
bool audio_terminate();
bool audio_start();
bool audio_stop();
double audio_getCurrentTime();

int ogg_openFile(const char *path);
void ogg_closeFile();
int ogg_seekToTime(float time);
float ogg_getLength();
void ogg_startDecoding();
