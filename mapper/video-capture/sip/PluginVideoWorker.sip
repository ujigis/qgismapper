%Module PluginVideoWorker 0

%Import QtCore/QtCoremod.sip
%Import QtGui/QtGuimod.sip





class RecordingParameters {
%TypeHeaderCode
#include <PluginVideoWorker.h>
%End

public:
	RecordingParameters(QString outputFile, QString codec, long bitrateInKBits, QString device, int width, int height, int fps, bool v4l2);

	QString outputFile;
	QString codec;
	long bitrateInKBits;

	QString device;

	int width;
	int height;

	int fps;
	bool v4l2;
};




class CameraMode {
%TypeHeaderCode
#include <PluginVideoWorker.h>
%End

public:
	CameraMode(int w, int h, int fps_);

	int width;
	int height;

	int fps;
};





class CameraCapabilities {
%TypeHeaderCode
#include <PluginVideoWorker.h>
%End

public:
	QList<CameraMode> modes;

	bool v4l2;
};


class VideoPreview : QWidget
{
%TypeHeaderCode
#include <PluginVideoWorker.h>
%End

public:
	VideoPreview(QWidget *parent /TransferThis/ = 0, int previewWidth=150, int previewHeight=100);

	int getWidth();
	int getHeight();

protected:
	void paintEvent(QPaintEvent *event);
};



%UnitCode
#include <PluginVideoWorker.h>
%End

bool initializeVideo();
bool uninitializeVideo();

bool isDevicePresent(const QString& device);
QStringList getDevices();
CameraCapabilities getDeviceCapabilities(const QString& device);

bool startRecording(QList<RecordingParameters> cameras);
void stopRecording();

bool isDeviceBeingRecorded(const QString& device);

void setPreviewForDevice(const RecordingParameters &source, VideoPreview *widget, int framesInterval);