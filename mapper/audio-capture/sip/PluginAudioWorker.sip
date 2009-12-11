%Module PluginAudioWorker 0

%Import QtCore/QtCoremod.sip
%Import QtGui/QtGuimod.sip



%UnitCode
#include <PluginAudioWorker.h>
%End

bool initializeAudio();
bool uninitializeAudio();

bool startAudio(int inputDevice = -1);
void stopAudio();

bool startRecording(const char *outputFile);
void stopRecording();

float getCapturedAudioPeak();

class AudioDevice
{
public:
  int index;
  QString name;
  QString api;
  bool isInput;
  bool isOutput;
};

QList<AudioDevice> devices();

int defaultDeviceIndex();
