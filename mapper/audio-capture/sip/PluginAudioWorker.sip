%Module PluginAudioWorker 0

%Import QtCore/QtCoremod.sip
%Import QtGui/QtGuimod.sip



%UnitCode
#include <PluginAudioWorker.h>
%End

bool initializeAudio();
bool uninitializeAudio();

bool startAudio();
void stopAudio();

bool startRecording(const char *outputFile);
void stopRecording();

float getCapturedAudioPeak();