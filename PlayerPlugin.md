# Player plugin #

Player plugin is a plugin for Quantum GIS software that enables users to replay recorded paths with more data data sources, e.g. audio and video. With GatherPlugin it creates a complete recording and playback solution.


## General data replay work flow ##

Once data are recorded by the gather plugin, they are transferred into computer used to convert the stored data to whatever format required. By opening selected recording (see GatherPlugin for clarification, what a recording is), the user not only gets view of path travelled during recording (which may be later processed in QGIS), but also he may replay audio and video tracks and more operations. These tracks currently mainly serve the purpose of tagging roads. For example, if the recording operator saw a one-way street, he could mention it in the audio track. Or this fact could be seen in the video stream. It's possible to extend the functionality in the future, e.g. export video to a group of bitmaps, cut recorded audio and create a sight-seeing instructor by using recorded data.


## Installation ##

**TODO**


## Basic user interface ##

The first time player plugin is started, something like the following should show up:

![http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_gui.png](http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_gui.png)


The "Data player plugin" dockwidget contains complete user interface of the plugin. It consists of several parts:

  * _Data source_ groupbox. The first edit line box contains path to directory containing recordings from gather plugin. After the path is entered (either by writing the path by hand or by pressing the " ... " button and browsing for the directory), press the _Load_ button to load the recordings list.
  * After the list of recordings is loaded, it's possible to select one of them in the list below. The selected recording is loaded and it's possible to use the rest of dialog afterwards. Also it's possible to delete the currently selected recording from disk by using _Delete_ button. The _Import..._ button enables user to import an arbitrary NMEA log file and create a regular recording from it (only containing the converted gps track, obviously).
  * _Replay_ groupbox. This part of dialog is used to control replay of the data. The main part of it is the replay position slider. Using this slider it's possible to rewind the recording to any recorded time. The current time and total time of recording is shown under the slider, to the right of _Play_ button
    * The Play button starts automatic replay of data at speed specified by the _Speed_ spinbox. At 100% the data is replayed at the speed at which it was recorded. Note that not all combinations of plugins enable replay at other than nominal speed (this is e.g. currently the case of audio plugin - if audio data is to be replayed, only 100% speed is available). The replay can be stopped by pressing the Stop button (it's the same button, that previously was "Play").
    * _Keep recorded GPS position in extent_ - this checkbox, if checked, will ensure that current GPS position in the recording will always be visible on the map canvas (i.e. the map extent will be moved, when needed, so that current GPS position is always within the extent).
    * _Map tool_ - this button, if checked, will set plugin's special map tool to be used instead of active QGIS map tool. This map tool enables source plugins to perform certain special actions by clicking their canvas items (like showing photos after clicking their map canvas icon). The standard functionality of player plugin map tool is regular map panning - when dragging map, it gets scrolled accordingly. If you however click on/near the GPS track, a second mode is used - after releasing the mouse button, the current position in recording is rewinded to the time associated with the point at the track (i.e. the recording is rewinded so that the gps position at current recording time is the about the same as the mouse position in map).
    * _Source plugins_ replay tab box. Replay options are described in the data source section for each source separately.
    * _Settings_ button. By pressing this button, a configuration dialog appears, containing additional configuration options of the player plugin (it's currently empty).

Basically the steps are:
  1. choose recordings directory
  1. press "Load" button
  1. click a recording in the list

After loading a recording the user should see the GPS track in map canvas and the plugin should be ready for playback:

![http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_recording.png](http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_recording.png)


On the screenshot you can see some standard plugins' tabs, a loaded track in the map canvas and a video plugin window. The following section describes interface used to navigate in the recording.


## Data Sources ##

The main part of the recording is the position data from GPS - stored in form of a GPX track. The track contains several pieces of information about GPS status at the time of gathering(=recording), and it is automatically displayed in the map canvas when the selected recording gets loaded. On the image above, it's the blue track.

### Gps ###

Apart from the track displayed on map canvas, there is more information in GPS tab. It probably contains all important navigation info - you can always dig more from raw NMEA data which are also recorded by gather plugin. The format of data displayed is a simple key-value table:

![http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_src_gps.png](http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_src_gps.png)

Probably the only two unclear values are "Time of record" and "GPS time of record". The first value is the time of computer at the time of recording the GPS data. GPS time is the time that was received by the GPS device. The two values should be preferably (for users sake) as close as possible, however only the computer time is used - GPS time is only stored for checking reasons.

### Audio ###

Audio source plugin enables user to replay audio using standard sound card output. The default system audio output is used - it's not possible to choose specific source inside plugin (do this using your system settings instead, please).

![http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_src_audio.png](http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_src_audio.png)

The only thing that the plugin allows to set is whether or not audio replay will be on during automatic data replay (when _Play_ is pressed). This is chosen by checking the _Active_ checkbox. Note that the _Active_ checkbox is only enabled if audio data is present in the recording. Also note that after activating audio replay it's not possible to change replay speed.


### Video ###

Video source plugin enables user to replay data previously recorded by the video source plugin of gatherer. After loading the recording, the combo box of the video tab is filled with stored video files. It should look like this:

![http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_src_video1.png](http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_src_video1.png)

Also, if _Replay active_ checkbox is enabled, the selected video file is opened in a separate window. Position in video file is synchronized with position in the recording - although there are some tolerances (which should stay under 1-2s). Please note that if video replay is active, the speed of replay is always 100% and can't be changed.


### Notes ###

Notes plugin enables user to see and read notes stored during recording. Unless a text note is clicked (see later), the notes tab looks following:

![http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_src_notes1.png](http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_src_notes1.png)

They are displayed the same way as during the recording - the note markers are placed on the map at the place where they were entered. Example of the map markers follows:

![http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_src_notes2.png](http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_src_notes2.png)

Green marker cross is placed where only a note without text was left. Blue one contain some textual information that is accessible by clicking the area of note marker - after clicking (if the player map tool is active), the note is displayed in the note tab.

![http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_src_notes3.png](http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_src_notes3.png)


### Photo ###

The photo source plugin doesn't have equivalent source plugin for gatherer (mainly because it doesn't make a lot of sense). The main purpose is to enable user to associate photos captured during recording with the track and display them at according parts of the track. The photos are displayed nearby the recorded track on map in small balloon-like boxes (see below). The main interface of plugin:

![http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_src_photo.png](http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_src_photo.png)

Every time new recording is loaded, thumbnails of photos have to be generated and loaded into memory. The progress bar on the top of the tab shows the progress of this operation. When finished, photos are placed on the map canvas and are ready to be worked with.

The most important is the _Add pictures from a directory_ button. After pressing it, a directory has to be chosen, from which the photos are copied into the recording and loaded. Each photo has to contain so called EXIF information, so that the photo source plugin is able to determine date and time of its creation and to insert it into appropriate part of recording correctly.

After photos are inserted into the recording, loaded and cached, it's possible to work with them further. List of available photos enables user to choose some of them and remove them by the appropriate button.

In case time was set differently on the recording PC and on the camera, the _Time offset of all photos_ might come in handy. Functions in that groupbox help changing the time of all photos to correct one (so that they fit correctly to the map). The functionality is of course completely manual - no offset detection of any kind is provided. After setting time offset of photos, it's possible to use the _Preview_ button - which causes that photos are moved only on the map. User might then check that the offset was correct - and if yes, it's possible to commit changes by using _Save_ button. The button causes storing photos with new times (the files' contents stay untouched, so no worries about JPEG quality degrading). This way it's possible to easily fix e.g. 1 hour differences between PC and camera time.


Another part of photo interface is placed on the map canvas - each photo is shown near the track in a balloon-like box:

![http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_src_photo2.png](http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_src_photo2.png)

By clicking the box (again, if player plugin map tool is active), a full version of the photo is displayed in an external window.

If there are more photos occupying the same map canvas space (so they would overlap), photos are grouped:

![http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_src_photo3.png](http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_src_photo3.png)

By clicking the box photos are expanded around it and it's possible to click individual photos (which works as with regular photo balloon):

![http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_src_photo4.png](http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_src_photo4.png)

Note that all external photo windows are closed after unloading the player recording (or loading another recording, for that matter).