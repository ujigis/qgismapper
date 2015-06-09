# Introduction #

Gather plugin is a plugin for QuantumGIS software, that enables users to record travel path and other accompanying informations - audio and video, for example. The primary purpose of the software (combined with player counterpart of the plugin duo) is to enable easy mapping of cities by using a vehicle, touchscreen, microphone and cameras.

After the data are recorded, it's possible to replay them later using player plugin (and thus use in some way, e.g. to create maps or note road types).


# General data recording workflow #

The following usage is assumed: User starts the qgis, configures output directory and data inputs (video cameras, audio devices...). After that, he starts recording data and 'traveling'. Data are continuously recorded and user is also enabled to leave short notes for the current position. Most of the data sources are visualized during recording (see sections below), so the user knows whether hardware is working as it should. When all planed places are driven-thru, the recording is stopped. All data stored between start and stop of recording are called a _recording_.

# Installation #

**TODO**

# Basic user interface #

The first time gather plugin is started, something like the following should show up:

![http://qgismapper.googlecode.com/svn/trunk/doc/gatherplugin/gather_gui1.png](http://qgismapper.googlecode.com/svn/trunk/doc/gatherplugin/gather_gui1.png)


The "Data gather plugin" dock widget contains complete user interface of the plugin. It consists of several parts:
  * _Start recording_ button. By pressing this button the recording is started, using the current settings of output directory and source plugins.
  * _Output groupbox_. Here it's possible to specify directory, where recordings are stored. It also contains free space information, that contains current free space in the specified output directory (well, disk where the directory resides, to be precise).
  * _Path preview groupbox_ . Here it's possible to configure visualization of path traveled (received from gps data source).
  * If _Follow own gps position on map_ is checked, the map canvas extent will always be moved so that current gps position is centered in it.
  * _Map canvas scale_ slider allows to choose scale of the displayed map.
  * _Keep recorder paths..._ checkbox, if checked, ensures, that after recording ends, the recorded path will stay on the map canvas. When unchecked, all previous paths are erased from the map.
  * _Source plugins_ configuration tab box. Configuration options are described in the data source section, for each source separately.
  * _Configure GPS data source_ button. By pressing this button, a configuration dialog appears, where it's possible to set up the GPS data source.
  * _Switch to simple interface_ button. Using this button it's possible to switch the dockwidget to  a smaller one - which is more of just an informative widget (it's not possible to set up much of the recording there). See simple interface subsection.

## Simple interface ##


By pressing the _Switch to simple interface_ button, the 'big' user interface reduces to a smaller one to only contain as little information as needed to know, that the recording is working correctly. This mode is useful e.g. for small touch screens:

![http://qgismapper.googlecode.com/svn/trunk/doc/gatherplugin/gather_gui2.png](http://qgismapper.googlecode.com/svn/trunk/doc/gatherplugin/gather_gui2.png)

It's of course possible to return to full interface by pressing the _Switch to full interface_ button. The _Start recording_ and _Free space_ widgets have the same functionality as before.

The main change is that there only is a _Recording sources_ groupbox. There are a few widgets inside it:
  * _GPS fix_ - indicates status of GPS device. If the icon is red, connection to gps device failed and no gps data is available. Yellow icon means successful connection to GPS device, but no GPS fix (i.e. the position is yet to be determined by gps device). Green icon means full operation mode.
  * _Audio recording_ - if checked, the audio is recorded.
  * _Video recording_ - if checked, the video is recorded (using the configured cameras). Also, if there is some error, the text of checkbox would indicate it.


# Data sources #

## GPS ##

This source plugin actually is a special type of plugin - it doesn't store any data :-) It's purpose is solely to inform user, in a visual way, about current GPS 'status'.

![http://qgismapper.googlecode.com/svn/trunk/doc/gatherplugin/gather_src_gps.png](http://qgismapper.googlecode.com/svn/trunk/doc/gatherplugin/gather_src_gps.png)


The GPS tab is split into two parts - top and bottom.

The top part may be in a simple or verbose mode (switched by clicking somewhere into the tab space). In simple mode only a sky graph is displayed, in the verbose one, also current position, orientation, altitude and other GPS parameters are displayed (see your GPS device's documentation for more informations).

The sky graph is basically a compass containing satellites' positions. The graph rotates according to current bearing - at each time point, the top part of graph is oriented to the direction given by bearing. In other words, if the bearing is the movement angle (depends on GPS device sometimes, but should be true most of the time), then if you hold the screen pointed in the direction of movement - e.g. north is always where the compass shows. Besides this information, the graph also contains satellites' positions on the sky (relative to current bearing and position) - each satellite is drawn with it's id, and is blue (if used to calculate current position) or grey (it's not...). The position of satellite on graph is given by it's angle and elevation.

The bottom part shows a list of available GPS satellites. Each column contains a satellite ID in the bottom part. Height of the bar depends on signal strength (the better signal, the higher the bar) - and numerical value of signal strength is placed above the bar. Also each bar has a color - blue, if the according satellite is used to calculate current position; grey otherwise.

### Configuring GPS input ###

Unlike other devices, the Gps device is configured using the "Configure GPS data source" button. The following dialog appears:

![http://qgismapper.googlecode.com/svn/trunk/doc/gatherplugin/gather_gpssettings.png](http://qgismapper.googlecode.com/svn/trunk/doc/gatherplugin/gather_gpssettings.png)

In the _GPS data source_ it is possible to choose one of the available GPS sources. Gather plugin currently supports the following sources:
  * _GPS serial device_ - support for serial devices providing NMEA data. When using this source, it's required to enter path to the serial device (could be e.g. /dev/rfcomm0 for linux and a bluetooth gps device). It's also required to specify baud rate of the serial connection (e.g. 3600, 38400). Note that a standard 8-N-1 'protocol' is used to communicate with the device at the specified baudrate.
  * _File_ - this option may be used to simulate a gps device and is mostly used to test the software. Parameters are (probably) previously recorded NMEA data file and number of characters read per second from the file.
  * _GPSd_ - to use data from GPSd daemon, it's required to enter it's address and port where it's listening. It's of course required to have the gpsd daemon running and configured to use it as a data source...

The connection to a gps device might be not stable (esp. if using e.g. bluetooth and there is some EM noise). Gather plugin therefore enables to specify, how often it should try to reconnect to a gps device (in case of lost connection) - and after how many failed attempts it should notify user about an error. Note that the notification is quite tough - the recording is stopped after lost gps connection and user is informed why. This is, because without valid GPS data it's pretty meaningless to continue mapping...


## Audio ##

Audio plugin enables user to record audio using standard sound card input. The default system audio source is used - it's not possible to choose specific source inside plugin (do this using your system settings instead, please).

![http://qgismapper.googlecode.com/svn/trunk/doc/gatherplugin/gather_src_audio.png](http://qgismapper.googlecode.com/svn/trunk/doc/gatherplugin/gather_src_audio.png)

The only thing that the plugin allows to set is whether or not audio recording will be on during data recording. This is chosen by the _Recording enabled/disabled_ button. It's only possible to change the settings outside data recording session. Note that after enabling of audio recording (regardless if data recording is on or off), a audio peak meter starts showing audio peak values. The purpose of this meter is to show some indication to the user, whether any audio is being detected/captured (by speaking to the microphone, the meter should show some activity).

## Video ##

Video plugin enables user to capture video from video devices to compressed avi files. All video cameras supported by kernel, using V4L(2) interface and providing raw output (like yuv, rgb - i.e. not jpeg) are supported. First time the plugin is started, a dialog like the following is presented to the uer:

![http://qgismapper.googlecode.com/svn/trunk/doc/gatherplugin/gather_src_video_devs.png](http://qgismapper.googlecode.com/svn/trunk/doc/gatherplugin/gather_src_video_devs.png)

The _recording enabled_ button is disabled until at least one video device is configured to be recorded.

### Defining used cameras ###

The configuration of cameras begins by choosing a camera from the list of available devices (you can use the refresh button, if the camera was added after program started - to get new list of available devices) and pressing _Add to used devices_ button. Video plugin automatically only recognizes devices within /dev filesystem, with filename beginning with 'video' string. If the camera isn't listed, and you know which device file it uses, it's possible to enter path to the device in the "custom" line edit widget (or press ... button to browse for the device). Again - only V4L(2) devices are supported.

After adding the camera to used devices, a tab is added, containing configuration options for the chosen camera:

![http://qgismapper.googlecode.com/svn/trunk/doc/gatherplugin/gather_src_video_dev.png](http://qgismapper.googlecode.com/svn/trunk/doc/gatherplugin/gather_src_video_dev.png)


### Configuring cameras ###

It's possible to choose mode of the camera - resolution and frames per second (FPS) recorded. Mode combo box pre-filled with available modes detected from the camera. However it's possible to enter custom value into the mode combo box. Note that the V4L2 doesn't guarantee, that the FPS will be the same that you choose. However - video plugin tries it's best to keep the FPS constant, so that the video is always recorded at constant speed. After choosing the mode, it's possible to enable the video preview - if you get some image there, it's almost certain, that the camera is working correctly. Otherwise, the camera probably doesn't support the selected mode combination (resolution and/or fps). This might have many reasons - you can see error messages in console.

Hint 1: Please note, that some cameras (or v4l drivers) don't particularly 'like' too fast changes of  mode (which could end up with camera being unable to provide any data until unconnected and reconnected to the PC).

Hint 2: If you need to configure more than one USB camera (e.g. four of them), it's possible that you will encounter problems with capacity of the USB bus. Some cameras don't support USB hubs (so more than one camera connected to one PC USB port will end up with error), and the bigger you choose resolution and fps, the less data rate is available to other cameras. It's therefore pretty problematic to have 2x 1024x768@30fps connected to the same USB port. There are more problems - all cameras we tested only supported different fps's virtually in driver - regardless what fps is chosen, the camera 'occupies' the same amount of data transfer rate of the usb port (so it doesn't really matter if you choose 1fps or 30fps).

Hint 3: As you might see by now, it's pretty tricky to get a few cameras running at the same time. We suggest the following workflow: add cameras, configure modes, enable camera previews. After this, you will see, which cameras are going to work during recording. This is, because after you start recording, the camera device 'connections' aren't restarted - so cameras showing data in previews are going to continue working during recording.


### Configuring compression codecs ###

The last thing that can be set is codec used to encode the video data:

![http://qgismapper.googlecode.com/svn/trunk/doc/gatherplugin/gather_src_video_enc.png](http://qgismapper.googlecode.com/svn/trunk/doc/gatherplugin/gather_src_video_enc.png)

Video plugin uses ffmpeg libraries to encode video - available codecs are thus equivalent to the ones ffmpeg is compiled with. In case of ubuntu and debian, the standard ubuntu 9.04 ffmpeg doesn't support enhanced codecs (because of patent issues) like mpeg4 and x264 - one is required to use e.g. mjpeg codec, which should always be available. For each codec it is possible to choose bitrate - use of this parameter is however codec-dependent. Please note that the more sophisticated codec you chooose, the more powerful cpu you need to be able to compress the data real time. In case the cpu is too slow, uncompressed data are stored in ram until compressed - and you might get into ugly memory-full problems. Please test that you are able to compress video in real time (and you have some cpu-power reserves) before you start using video recording in terrain.

All available codecs can be listed by using the `ffmpeg -formats |grep DEV` command. Not all of these codecs are usable (e.g. bmp would output a bunch of bmp images, which is not supported  by gatherer) - if you are unsure whether particular codec is 'good', try setting it and you'll see, whether it works.

Recommended codecs, if installed, are mpeg4, x264, mpeg2 and mjpeg (in specified order). The better codec, the less disk space is needed, the better the quality - however, also more powerful cpu is needed, as mentioned. The optimal bitrate depends on chosen codec and mode - it's recommended to try out different bitrates with chosen video mode and codec (and replay the data afterwards - to see if there aren't too many compression artifacts). The bitrate and codec setting is common for all cameras - so be sure to test the setting for the best mode, whether it's sufficient.

## Notes ##

Notes plugin enables user to store notes during the recording - useful if e.g. microphone doesn't work, or if the notes are processed automatically later. Notes plugin functionality is only available after recording starts (for the obvious reasons).

![http://qgismapper.googlecode.com/svn/trunk/doc/gatherplugin/gather_src_notes.png](http://qgismapper.googlecode.com/svn/trunk/doc/gatherplugin/gather_src_notes.png)

Once the recording started, the _Mark current position_ button is enabled. After clicking it, the current position on the map is marked (a red cross is shown on the map - see the example picture below). Also, an edit widget is shown under the button, where it's possible to add a note to the mark. After the note is entered, it's required to press _Add note_ button. After adding the note, the mark on map changes color to blue (to indicate that it contains a note). After pressing the _No note_ button, or the _Mark current position_ button again, the last entered mark is considered 'note-less' and is colored to green.

![http://qgismapper.googlecode.com/svn/trunk/doc/gatherplugin/gather_src_notes_marks.png](http://qgismapper.googlecode.com/svn/trunk/doc/gatherplugin/gather_src_notes_marks.png)



# Example of setup procedure #

The following short text gives an example on how to setup gather plugin for a recording session.
  1. Install qgis and gather plugin. Start qgis and enable the gather plugin in plugin manager.
  1. Configure output directory - should be (for best performance) placed on a local harddrive.
  1. Configure GPS device. After the device is configured, the GPS position should be shown in the GPS source tab.
  1. Now, depending on what devices are going to be used, configure them and enable the recording. Please remember the Hint 3 of video camera setting.
  1. Perform a test recording before the real usage - to be sure that everything is working as required, a test replay (using player plugin) is recommended.
  1. Record=gather data.
  1. Transfer data from recording computer to the replay/processing one.