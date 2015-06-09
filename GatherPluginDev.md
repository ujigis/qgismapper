# Gather Plugin - Developer's Guide #


## Architecture ##

To provide some first insight into the architecture, an overview diagram follows - to show approximately how the plugin is organized:

![http://qgismapper.googlecode.com/svn/trunk/doc/gatherplugin/gather_overview.png](http://qgismapper.googlecode.com/svn/trunk/doc/gatherplugin/gather_overview.png)

Main parts of the gather plugin are inside the gatherplugin.py and Gatherer.py files. These provide the most basic functionality of the plugin, managing all other functionality.

The GUI of plugin is provided by DockWidget.py and DockWidget\_simple.py, which do provide 2 versions of the plugin user interface to user. Additionaly, DlgSettings.py provides additional configuration options for the plugin.

The only device that is handled directly by gather plugin is GPS source. The GPS devices are operated by GpsDaemon.py, GPS data are parsed by NMEA.py.

All other devices are handled by so-called Source plugins, which reside inside the SourcePlugins directory.


## Components ##

### GatherPlugin ###

The `GatherPlugin` class implements the core of the plugin - the QGIS required functionality, and organizes the other parts of plugin to work together.
Most parts of the code are self-explanatory (and/or documented in the code) - so here is only an overview of what is being done in the class, and why/how:


#### Loading and Unloading ####

After the plugin is loaded by QGIS, the `GatherPlugin.initGui()` method gets called. The complete initialization of plugin happens here (as recommended by QGIS docs) - dock widgets are created (and one of them is shown), configuration and source plugins are loaded, gps daemon is created... At `GatherPlugin.unload()`, the opposite is happening - configuration is saved, source plugins are unloaded, and interface gets destroyed.

#### Data recording ####

Data recording is started by `recordingStart()` method and stopped (obviously) by `recordingStop()`. The current recording status (whether it's on) is held in the `GatherPlugin.recording` member variable.

A few things are required to start recording. The GUI is prepared (by initializing path preview layer and changing dock widgets' visual appearance), and a Gatherer object is created 'started' in `GatherPlugin.recordingStartGatherer()`. The opposite has to happen at recording termination.


#### Communication with Gatherer ####

As the gatherer events happen asynchronously, the `Gatherer` to `GatherPlugin` communication is happening using a event mechanism. Each time Gatherer needs to "tell something", it emits a `gathererEvent(PyQt_PyObject)` signal, which is then further processed by `GatherPlugin.processGathererEvent()` - and distributed to appropriate `GatherPlugin.processGatherEvent_*` methods (the name of called method is created from the first parameter of the signal - e.g. `gatherEvent("test", 1, 2)` would be "forwarded" as call to `GatherPLugin.processGatherEvent_test(1,2))`. Currently only two signal types are processed - `newTrackPoint` and `recordingTerminated`.

The other way of communication (`GatherPlugin` to `Gatherer`) is performed directly - by calling methods of `Gatherer` object.


### Gatherer ###

The Gatherer object serves as the main controller thread for the recording (=gathering) process. It's meant as one-run-per-life object - each recording should use a new `Gatherer` object.

Because the Qt library doesn't support GUI processing in threads other the main one, the Gatherer architecture had to be designed in a not-so-straightforward way. To simplify design of (trivial) source plugins, Gatherer is designed in way that `startRecording` and `stopRecording` methods of source plugins are called from the main application thread. Source plugins (SP) may update their UI out of the separate Gatherer thread (other SP methods are called from this new thread). The following recording process flow chart could clarify the situation:

![http://qgismapper.googlecode.com/svn/trunk/doc/gatherplugin/gather_gatherer.png](http://qgismapper.googlecode.com/svn/trunk/doc/gatherplugin/gather_gatherer.png)

From the diagram it's possible to see what methods are called in which thread's context. It's also possible to see how the recording-terminated event is sent to GatherPlugin. After the recording is terminated, GatherPlugin calls `Gatherer.terminateAndCleanup()`, which in turn calls `SourcePlugin.stopRecording()` and `gpsDaemon.stopRecording()`.


#### Data recording logic ####

The current Gatherer design assumes two types of data being recorded - one that doesn't necessarily need real-time/heavy processing, and a second one of opposite type.

Workflow of simple data is that after `startRecording()` is called, they briefly initialize what they need and they do finalization at `stopRecording()`. During the recording, the `pollRecording()` is periodically called to get any new data (since the last poll) and store it as needed. It's assumed that neither of the three methods takes too much time - otherwise it would block GUI thread and/or polling of other source plugins.

More time-precision/cpu power dependent data need of course special treating. Gatherer assumes that during the `startRecording()` another separate processing thread (or threads/process(es) if necessary) is created inside the source plugin and it is terminated cleanly (again by the source plugin itself) after `stopRecording()` is called. The `pollRecording` method is typically useless in this case - the whole recording is in hands of the source plugin.


### UI ###

There are three main GUI components that the GP uses. Two are dock widgets that inform user about the current status of recording and enable him to do some changes in configuration (recording, source plugins, visual appearance of recorded track etc.). Moreover there is `DlgSettings` dialog that currently enables user to configure the GPS device. As the `DlgSettings` dialog is pretty trivial, we won't discuss it here any further.

Two types of dock widgets were implemented, because it's assumed that the GP could be used with small screens - and the complete 'big' dock widget occupies too much of screen space. The small dock widget therefore only contains the most important information to only inform user whether the recording is still uninterrupted by some errors.


#### DockWidget ####

Apart from standard recording controls, in the big dock widget there is a place where custom widgets of source plugins may be placed - to enable user changing their configuration. To simplify the insertion, each source plugin class has to be derived from QWidget class - and it is inserted into the SourcePlugins tab control under title specified by `SourcePluginObject.name` string.

Apart from handling user GUI actions (either by updating other child widgets properties, or by forwarding messages to GatherPlugin controller), the DockWidget class is pretty much trivial.


#### DockWidget\_simple ####

The simple dock widget (SDW) shows only recording button, a few status lines/checkboxes and a button to "return" to "full DockWidget".

The SDW (currently) doesn't update its contents according to installed source plugins - it's hard-coded and the source plugins may retrieve appropriate checkbox by calling the `GatherPlugin.getRecordingEnabledAuxCheckbox()` method with the name string of requested widget (mostly a checkbox). The name is to be the same as the `SourcePlugin.name` (e.g. "Video") to keep some order. If widget with specified name isn't contained in the dialog, the method returns `None`. "Gps", as exception, returns a (`GpsStatusWidget`, `QLabel`) pair - source plugin `PluginGps` expects this.

Source plugins are completely unlimited on what to do with the checkboxes - it's however recommended that they work the same way that "Recording enabled" checkbox would work. It's also possible to change string of the checkbox (keep it short and informative - even in case of error; also remember to manipulate with the checkbox only in the main GUI thread).

Note that the `GatherPlugin.getRecordingEnabledAuxCheckbox()` functionality is only available to source plugins when (and/or after) the `SourcePlugin.finalizeUI()` is called.

## GpsDaemon ##

GpsDaemon class communicates with configured GPS device, and provides the received GPS data for other components of gather plugin. As the daemon's only purpose is to read the data from device that user specifies, it always takes configuration from the `GatherPlugin` "parent object" - which in turn gets the configuration parameters from user set in `DlgSettings` dialog.


### Initialization ###

There are two ways of opening a GPS device by the daemon. The first one is calling the `resetGpsSource()` method. The other way is automatic - after a connection with GPS device is interrupted, daemon automatically tries reopening it after user-specified time. This is done by starting a `retryOpeningTimer` and calling `resetGpsSource()` after the timer finishes. Also, an internal counter of how many unsuccessful reopenings took place is being held (in `retryCount` member variable) - after the maximum retry count is reached, the `ok()` method of daemon starts returning `false`, to indicate error condition of the GPS data source.

Currently, 3 GPS device types are supported:
  * serial port (`GpsSource_serial` class)
  * file (`GpsSource_file`)
  * GPSd (`GpsSource_gpsd`)
All the device type classes use the same interface:
  * `__init__` - the specified device should be opened
  * `poll()` method should read all the new data from device
  * `ok()` should return true if device is still opened
  * `close()` should close the device
Initialization of GPS device may take some time and might render QGIS unresponsive during that time. For example, opening of a Bluetooth serial connection may take 10 seconds - and ultimately fail if the device isn't found after that time. That's why initialization of GPS device (by creating one of the mentioned objects) happens in a separate thread - `GpsDaemon_opener`. After the device opening finished (successfully or not), the control gets to `GpsDaemon.onOpenGpsSource_finished`, that either finishes the initialization of daemon, or reschedules next opening attempt.


### Data reading ###
The daemon periodically calls `poll()` method of the GPS source object to receive new data (see `GpsDaemon.timerEvent()` and `GpsDaemon.fetchData()`). If there are any new data, they are appended to data buffer and the buffer is parsed line-by-line by `GpsDaemon.processNmeaData()` method - until the last complete line. All processed lines are removed from data buffer. After a GPRMC NMEA sentence is found (which means new position information), a `newTrackPoint` signal is emitted - to let all the interested parties know about the event.

Also, if daemon is in recording mode of daemon (`GpsDaemon.startRecording()`, `GpsDaemon.stopRecording()`), the `processNmeaData()` method also extends the GPX file by adding new track points - when new valid position is received from GPS device.

### Retrieving data from daemon ###

Other parts of plugin may read parsed data from a NMEA object that is held inside of the daemon in the `GpsDaemon.nmeaParser` variable (which is only valid, when `GpsDaemon.ok()` returns `True`).

### GPX data recording ###

Gps daemon is capable of storing parsed GPS data into a NMEA and GPX file. The recording is started by calling `GpsDaemon.startRecording()` with appropriate files' paths. After the recording isn't required any more, the `GpsDeamon.stopRecording()` has to be called, so that the recorded files are correctly flushed.


## Source Plugins ##

Source plugins extend supported recording devices of the gather plugin.

All source plugins are placed in the SourcePlugins subdirectory of the gather plugin directory. Apart from source plugins' implementations, it contains init.py file which provides an abstraction layer above source plugins to gather plugin. Using methods in init.py, it's possible to call a single method of all loaded plugins etc. All functionality provided by the 'file' is pretty straight-forward - however, all functions are well documented, so please continue reading code documentation if interested.


### Audio ###

Audio source plugin (ASP) currently consists of two separate parts - python wrapper and a c++ recording library.

#### Python wrapper ####

The python wrapper is straightforward and it's not doing any special operations except for calling the c++ library methods. One interesting part of the wrapper is the audio-peak indicator (see AudioStatusWidget.py) - after the recording is enabled, wrapper periodically asks the c++ lib, what's the current audio peak, and sets the `AudioStatusWidget` peak value appropriately.

Recorded audio files are stored inside the recording directory, and it's "Audio/" subdirectory - in files named according to the current system date and time.

#### C++ part ####

The library implementation consists of 2 more parts - the library itself, and a SIP wrapper (to enable easy usage inside python). We'll only discuss the library here as the SIP wrapper is a regular way of connecting c++ and python code.

Gather plugin requires that the audio recording is separated from audio capture in a sense that audio capture may be running without the recording (i.e. recording might be turned on/off). To give an overview in what order the audio processing methods should be called, see the following diagram:

![http://qgismapper.googlecode.com/svn/trunk/doc/gatherplugin/gather_audio_workflow.png](http://qgismapper.googlecode.com/svn/trunk/doc/gatherplugin/gather_audio_workflow.png)

Note that the method `getCapturedAudioPeak()` (not present in diagram) may be called anywhere between `startAudio()` and `stopAudio()` calls.

As you can see the audio processing workflow has a kind of reentrant nature, and is designed in a logical and straightforward way.

The audio capture is implemented by using the [PortAudio library](http://www.portaudio.com/), the compression/recording by using [Ogg Vorbis library](http://www.vorbis.com/).

Audio capture is started after calling `startAudio()` metod. Audio device is initialized by using the PortAudio methods. Until it's stopped, the `paCallback()` is called by PortAudio - with every new audio frame. Unless the recording is started, the method only stores audio peak from the audio frame, which may be later retrieved by user. Only the maximal peak value since the last `getCapturedAudioPeak()` is stored.

The recording process is a bit more complicated. After calling `startRecording()`, a ogg vorbis stream and encoder are initialized, an audio buffer is created and audio compression thread is started. The audio buffer is a simple one, and is implemented inside the `PluginAudioWorker_SamplesBuffer.c` file.

After recording started, the `paCallback()` appends new audio frames to this buffer. The `recordingThreadFct()` then takes frames out of the buffer and forwards them to the vorbis compression - and the compressed packets to ogg storage.

When recording stops, only the recording thread is stopped - at termination it ensures, that files are flushed and closed, and that the audio buffer is freed.

### Gps ###

The GPS plugin uses NMEA decoded data from the Gather plugin and shows them in a user-convenient way using the `SatellitePositionsWidget` and `SatelliteSignalStrengthWidget` widgets. There is no interesting data processing in here.

Because of the nature of GPS info displaying, the `start`/`stop`/`pollRecoding` methods are empty and the GPS view is updated each time the GPS device is (re)connected and when new GPS data are received (see GpsDaemon signals). The NMEA data are read afterwards and forwarded to already mentioned widgets.

Both widgets only contain a drawing code, there's nothing special inside.


### Notes ###

When recording starts, a "Notes/" subdirectory is created in the recording directory and an empty XML document is created - it's flushed at once when recording stops into the "Notes/notes.xml" file.

The plugin doesn't do much data processing - after receiving input from user, it only extends the XML file with "note" node, having a "time" attribute (which is the time when user clicked _Mark current position_ button), containing the entered note text (if any).

Interesting part (although not that much) of the plugin is the way how canvas items are kept on the map canvas. Each time a new marker is created, a new canvas item is created too (at current GPS position). Later, when user confirms the note (by either adding some text or pushing _No note_ button or creating another marker), the last (temporary) canvas item is removed and a new "permanent" canvas item is added to map canvas (and to the canvas items list).

When the recording is stopped, the user may want to hide the recorded track (and associated stuff) from map canvas. The plugin is notified and calls its `clearMapCanvasItems()` method to clean up the markers.


### Video ###

Video source plugin consists of two parts - much like the audio plugin - python wrapper and c++ library (`PluginVideoWorker`). This plugin should be able with little changes work also on windows or other platforms. For all video handling it uses [ffmpeg](http://ffmpeg.org/). It's a cross-platform library for recording, converting and streaming of video and audio.

The following diagram shows most interesting calls in the plugin (and which parts are used how):

![http://qgismapper.googlecode.com/svn/trunk/doc/gatherplugin/gather_video_dia1.png](http://qgismapper.googlecode.com/svn/trunk/doc/gatherplugin/gather_video_dia1.png)

#### Python part ####

The python part of plugin provides mostly only GUI and connection between Gatherer and `PluginVideoWorker`. It enables user to configure cameras and codecs. When recording is started, it creates the required directory and tells `PluginVideoWorker` from which camera(s) to capture video and where the encoded streams will be saved.

##### Video preview #####

Each video device is configured in a separate `V4lTab_Widget` widget. The widget receives device path. Then it asks `PluginVideoWorker` what are the video capabilities of the device by calling `PluginVideoWorker.getDeviceCapabilities()` and fills the dialog with received capabilities.

Even before recording starts, the PluginVideoWorker allows opening of the device and showing image preview. For this purpose PluginVideoWorker provides a special widget - `PluginVideoWorker.VideoPreview()`. After user checks that he wants to see the video preview, the `VideoPreview` widget is created (see `V4lTab_Widget.onActivatePreview()`) and associated with specified device and configuration (`V4lTab_Widget.connectPreviewToRecording()`).

##### Video recording #####

When video recording is started the `PluginVideo.getRecordingParameters()` is called - it only goes through configured video devices' widgets/objects and ask for their configurations. Also, it appends encoder settings and target filename to recording configuration. After it's retrieved, configurations are forwarded to `PluginVideoWorker.startRecording()`.

During the recording, recording status is periodically polled from PluginVideoWorker - and in a case of error, user is notified by setting informative text in appropriate widgets in both `DockWidget` and `DockWidget_simple`.

When video recording is stopped, `PluginVideoWorker.stopRecording()` is called.


#### PluginVideoWorker (C++ part) ####

This module, like the similar audio counterpart, consists of two parts - the main library code and a SIP wrapper, which is trivial and won't be discussed any further here.

The PluginVideoWorker library itself consists of four main parts:
  * main dispatch code (placed in PluginVideoWorker.cpp)
  * `GatherThread` class
  * processing classes (`ProcessThread`, `CompressThread`, `PreviewThread`)
  * `VideoPreviewWidget`


##### Recording session #####

PluginVideoWorker must be first initialized before calling any other methods and uninitialized once the work is done. The following diagram could explain the "situation" visually:

![http://qgismapper.googlecode.com/svn/trunk/doc/gatherplugin/gather_video_dia2.png](http://qgismapper.googlecode.com/svn/trunk/doc/gatherplugin/gather_video_dia2.png)

What it basically shows is that all methods may be used anywhere between `initializeVideo()` and `uninitializeVideo()` and `start`/`stopRecording()` should always be used "together". Of course `stopRecording()` has to be called before `unitializeVideo()` if `startRecording()` was used. Please note there are missing arrows (for simplicity) going from boxes below initialize/uninitializeVideo() back to the vertical line on the left. Moreover all the methods may be called between start/stopRecording() calls. Although the diagram isn't too good, we hope the reader will understand the workflow :-)

Typically, user first calls `initializeVideo()`. After that, `getDevices()` is called to retrieve available video devices. It's possible to enumerate devices' capabilities by calling `getDeviceCapabilities`. Client application then prepares list of `RecordingParameters` structures and gives them to `startRecording()` function. Once enough data has been recorded, `stopRecording()` has to be called. If no more data are to be recorded, also `uninitializeVideo()` should be called to free occupied memory. Even outside the recording session it's possible to call `setPreviewForDevice()` with camera settings and `VideoPreview` widget as parameters - this will automatically start device capture, if needed, and show frames from the device in the specified widget.


##### Core of the module #####

PluginVideoWorker.cpp file contains the core code of the PluginVideoWorker library. This file implements the library's interface using other parts of the module code.

Currently the code is written to support only V4L(2) devices - but it shouldn't be a big problem to extend the support to e.g. VFW windows interface.

`getDevices()` method currently only enumerates `/dev/video*` files and returns the result list.

`getDeviceCapabilities()` uses V4L(2) ioctl calls to first determine whether the device is v4l or v4l2 type. After that it uses the specified v4l version's iocalls to enumerate available camera's video modes. V4L only provides simple enumeration, so no magic there. For V4L2, `getDeviceCapabilities_enumFps()` and `getDeviceCapabilities_enumFrameSizes()` are called (recursively) for all available pixel formats of camera. In case no formats are found this way, a fallback is used - by calling VIDIOC\_G\_FMT V4L2 ioctl.

After device parameters are prepared, the `setPreviewForDevice()` or `startRecording()` may be called.

For threading, a custom `PThread` class is implemented (see `PluginVideoWorker.h`), from which all threads in the library are derived. This class is derived from `QThread` and is primarily designed for convenient starting/stopping of threads. Entry point of the `PThread` class is `doRun()` method - which should call the `shouldStop()` to determine whether user wants the thread to stop and quit. User may call the `stop()` method which will turn on the flag and block until thread finishes.

VideoWorker core keeps list of active devices in the `cameraProcesses` list. Each structure in the list contains all objects (widgets, threads, misc. parameters) associated with a single recording/video preview session.

A single camera process always contains a gather thread and a processing thread (some objects derived from `ProcessThread` class). The processing thread may be either `PreviewThread` object (derived from `ProcessThread`) or `CompressThread` object (derived from `PreviewThread`).

If only `setPreviewForDevice()` is called, no compression is required. A camera process is created that gathers data from camera, and additional `PreviewThread` is started to show captured frames. If a recording session is already started for the camera (see below), `PreviewThread` isn't of course created - instead the preview widget is passed to existing `CompressThread` object.

At `startRecording()` however, the camera process uses a `CompressThread` object which is also able to provide the `PreviewThread`'s functionality, but additionally compresses the captured frames into .avi file. If there already was a preview session active for the specified camera, only the `PreviewThread` object is destroyed - leaving the `GatherThread` running. Thanks to this strategy the camera device isn't reopened and in case of V4L(2) devices may save some trouble (as these cameras don't particularly 'like' being reopened in short time intervals).



##### GatherThread #####

After starting the thread, it first opens the video device by using ffmpeg library. After that the thread loops (until it's told to stop) reading new frames from the device and enqueing them to a list of frames. Each frame is allocated separately so in case there's a too long gap between enqueing and picking up the frame, the memory usage might get pretty nasty.

As the initial opening of video device might easily take seconds, the gather thread counts the time (number of 'lost' frames at current FPS, to be precise) between start and end of opening of the device. This information might later be used to synchronize the received video data.

As for the synchronization purposes, current frame number (again, at current FPS) is also stored in the `frame->pts` of the enqueued frame.

Some cameras don't keep the FPS specified at opening the device. If the real FPS is bigger than previously set (which could happen e.g. if there's too much light in the scene - the camera increases the frame rate), unused frames are discarded in `enqueueFrame()`.

The `restartCounters()` is used when `PreviewThread` is switched for `CompressThread`, to simulate a start of gathering. The call keeps the device opened, but empties the frames buffer and initializes current frame number to 0 (which virtually means that video device was opened with zero delay).


##### ProcessThread #####

Process thread is associated `GatherThread` object at its creation. From this gather thread it then periodically tries to receive new frames and process them in some way. This behavior is common for both compress and preview threads - that's the reason why they are derived from this class.

The processing thread also ensures that the correct FPS is received by `processFrame()`. This means that when receiving first frame, `GatherThread::getInitialBlankFramesCount()` is called to determine how many frames were missed during the opening of device. This amount of copies of first frame are then inserted into the frame stream received by `processFrame()`.

Also, if the gather thread doesn't provide enough frames for current FPS (i.e. current FPS is less than the preset one, which could happen in case of low light - cameras tend to prolong exposure, thus reducing FPS), the skipped frames are "filled" with copies of last frame before the skipped one(s).


##### PreviewThread #####

The `PreviewThread` is pretty simple - after initializing with preview widget, a software scaler is set up, which will transform received video frames into RGB frames of required dimensions. After that, the `processFrame()` calls `processPreview()` method which in turn calls the software scaler. After the bitmap is converted, a `frameReady()` signal is emitted to let the `VideoPreview` widget know that it should redraw the current image (`frameReady()` signal is connected to the `updatePreview()` slot of `VideoPreview` object). The data is stored inside the preview widget object, so no further calls to `PreviewThread` are required to redraw the image.


##### CompressThread #####

The `CompressThread` class extends `PreviewThread` class by frame encoding functionality. Apart from calling parent class's `PreviewThread::processFrame()`, `encodeFrame()` is called for each frame.

Of course, before any processing takes place, output file and codec has to be prepared. First format muxer is initialized and a video stream created inside of the format (`initFormat()`, `addVideoStream()`). Next, the chosen codec is opened and configured - and in case the destination video pixel format is different from the captured frames' format, a temporary picture is allocated (`initCodec()`).

The `encodeFrame()` then takes each frame, converts it to target pixel format (if required) and forwards the frame to ffmpeg's codec. The encoded data is then packed into `AVPacket` frame and frame written into the output file.

When the compression is to be closed (`closedVideo()`), a trailer of the file is written, occupied memory is freed and the output file closed.

Although the compression code might look a bit complicated, it is mostly just filling of ffmpeg's structures.


##### VideoPreviewWidget #####

The preview widget's only functionality is displaying the contents of contained bitmap. Algorithm used for this isn't currently too fast (effectively it first converts `AVFrame` to a memory-stored PNM image which is then converted to `QImage` and drawn), but it's enough (we think) for a preview.

Contents of the widget are, as for any other widget, redrawn whenever a `paintEvent()` event is received.

### Creating a source plugin ###

A source plugin provides a interface for gather plugin to record data from a device. Source plugin interface is pretty simple and straightforward. To create a source plugin, one has to create a file named Plugin`*`.py (where `*` stands for a alphanumeric string) in the SourcePlugins directory of the gather plugin. A sample implementation of a plugin is placed in PluginDummy.py, distributed with the project.

The file has to contain 2 things - a factory function and a definition of plugin class. The factory function (`getInstance()`) creates the plugin object and returns it. Most of the time, the method will probably look like the one in PluginDummy.py

#### Plugin object functionality ####

The plugin object has to provide some required functionality in order to work correctly. First of all, the object has to be derived from `QWidget` as it is used in the user interface as a configuration tab. The widget is inserted to the tab control automatically and has title based on the object's property "name" (which is also a required).

After the GP interface is fully initialized, the plugin's `finalizeUI` method is called. After this call, the plugin may use all the UI of gather plugin, e.g. call controller's method `getRecordingEnabledAuxCheckbox`.

The pair of methods `loadConfig()` and `saveConfig()` serves their obvious purpose. They receive a root element of a XML file which they should process/store to.

The main functionality of recording plugin is handled by methods `startRecording()`/`stopRecording()` and `pollRecording()`. After the `startRecording()` is called, the plugin should start recording, while not blocking the parent thread. The `stopRecording()` should do the opposite - immediately stop recording.

The `pollRecording()` method is somewhat special - it's called a few times a second and is can be used for data sources which do not require real-time operation (an example could be a data device with big buffers). Note that `pollRecording()` too shouldn't block the parent thread for too long, as this would block the whole UI and also other recording plugins using `pollRecording()`.

Note that all these methods `startRecording()`/`stopRecording()` and `pollRecording()` are run in the UI thread, so the commands inside of these methods may access UI without locking problems etc.