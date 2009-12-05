%Module ladybug 0

%Import QtCore/QtCoremod.sip
%Import QtGui/QtGuimod.sip

%UnitCode
#include <ladybug.h>
#include <ladybugwidget.h>
#include <ladybugstream.h>
%End



class LadybugFrame
{
public:
  LadybugFrame();

  QImage previewImage(int cam);

  int framesBehind;
  bool valid;
  unsigned int frameBytes;
  bool hasPreview;
  
  // preview images not accessible directly to avoid conversions
  //QList<QImage> preview; //[6];

  double megabytesWritten;
  int framesWritten;
  int framesDiscarded; // num. of discarded frames due full write buffer
};


class LadybugCounter
{
public:
  LadybugCounter();
  void reset();

  int framesGood; // correctly received frames
  int framesInvalid; // completely invalid frames
  int framesMissing; // frames from the sequence not caught
};


class Ladybug : QObject
{

public:
	Ladybug();
	~Ladybug();
	
	bool init();
	
	bool exit();

  bool isActive() const;

  QString errorMessage();
	
  void setSerialHead(unsigned long serial);

  QByteArray fetchCalibration();
	
	unsigned long serialNumBase();
	unsigned long serialNumHead();

  void startRecording(QString streamName);
  void stopRecording();
  bool isRecording();

  void setPreviewSettings(int camMask, bool color, int interval);
  void previewSettings(int& camMask /Out/, bool& color /Out/, int& interval /Out/);

  bool setJpegCompression(bool autoControl, int jpgQuality, int bufferUsage);
  bool jpegCompression(bool& autoControl, int& jpgQuality, int& bufferUsage);

  LadybugCounter& counter();

  void setCurrentGpsInfo(LadybugGpsInfo& gpsInfo);

public slots:
    void receivedFrame(LadybugFrame frame);

signals:
    void capturedFrame(LadybugFrame frame);
	
};



class LadybugWidget : QWidget
{

public:
  LadybugWidget(QWidget* parent = NULL);

  ~LadybugWidget();

  bool openStream(QString baseName);

  bool closeStream();

  class CameraPosition
  {
    public:
    CameraPosition();
    QPointF offset;
    int size;
    double zoom;
  };

  virtual QSize sizeHint () const;

public slots:
  void seekToFrame(int frameId);
  void seekToTime(uint msecs);
  void pause();
  void updateVideoPlayback();

protected:
  void paintEvent(QPaintEvent* e);
  void keyPressEvent(QKeyEvent* e);
  void closeEvent(QCloseEvent* event);

  uint cameraMask();

};

class LadybugGpsInfo
{
public:
  LadybugGpsInfo(double lon_ = 0, double lat_ = 0, double alt_ = 0, QDateTime time_ = QDateTime());

  bool isValid() const;
  QByteArray getGPGGA() const;

  double lon,lat,alt;
  QDateTime time;
};
