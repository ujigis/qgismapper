# Player Plugin - Developer's Guide #

## Structure ##

Structure of the player plugin is different from the one of GatherPlugin because of the difference in functionality.

The main part of the player plugin is implemented in the `PlayerPlugin` class. It provides the most basic functionality of the plugin and manages all other functionality. Other important parts are the `DockWidget` (providing GUI of the plugin), `ReplayMapTool` (enables user easy recording examination) and Source plugins (replay helpers for different types of recorded data). The following diagram shows simplified architecture of the player plugin:

![http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_overview.png](http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_overview.png)


## Components and architecture ##

### PlayerPlugin ###

`PlayerPlugin` class is the one that controls the workflow of whole plugin and interconnects its parts. Apart from providing functionality required by QGIS, it handles GUI requests (like loading a new recording, starting/stopping replay) and executes necessary actions or forwards the action execution requests to other components.

The basic structure of the class is very alike to `GatherPlugin` class. Class consists of three logical parts:
  * GUI
  * replay
  * "support" functionality

#### Initialization and finalization ####

After the plugin is loaded by QGIS, the `PlayerPlugin.initGui()` method gets called. The complete initialization of plugin happens here (as recommended by QGIS docs) - dock widget is created, configuration and source plugins are loaded, map tool is created... In `PlayerPlugin.unload()` the configuration is saved, source plugins are unloaded and interface gets destroyed.

#### GUI operations ####

The main GUI-related functionality implemented in PlayerPlugin is the recordings list manipulation - implemented by `*Recording*` methods of the class. These methods react on user request by e.g. reading contents of specified recordings directory (and displaying it in the dedicated list widget) and loading/unloading the specified recording. All operations, except for recording loading, are simple.

When a recording is about to be loaded, first it's tried to read the recorded GPX file into a `GpxFile` class. If the attempt is successful, previous recording (if exists) is unloaded and loading of the new one continues. This is done by creating a track preview vector layer and by telling all source plugins to load the current recording. Finally a current in-recording position map canvas item is created.

Unloading a recording is pretty much reversed algorithm - first replay is stopped (if in progress), then source plugins are told to unload recording, map layer is removed and finally the position marker and `GpxFile` object are freed.


#### Replay ####

There are two basic ways of reviewing recorded data - either by manually rewinding the recording and using the canvas items placed on map canvas or by starting automatic replay. These two are similar in some ways, thus parts of the implementation are common for them both.

We'll first discuss the automatic replay - the rest of replay code will only be an extension of the same principles.

Replaying data in PlayerPlugin means that all replayed output (the current GPS position and other source plugins' data output like audio and video) has to be continuously played and synchronized - so that the current video image is shown at appropriate GPS position etc. Obviously there are data types that require less time-accuracy than others (e.g. glitches in audio replay are much more disturbing than occasional glitches in video replay). This idea was the main one when designing the player architecture. Unfortunately synchronizing two or more basically unknown data types' replays is a very hard task - even an A/V synchronization in simple video players is a non-trivial task. Because of this problem, it was decided to only try to keep the synchronization in reasonable boundaries.


##### Timing #####

The replay itself is controlled by a timer. This is the most interesting part of player architecture. Because of the already mentioned different time-accuracy of different data types, player enables external timer sources (provided by source plugins) - and provides an internal one for case when no external is available. All external timer sources are currently considered to have the same accuracy - thus if there are more sources available, a (virtually) random one of them will be used.

The timer source may be set by calling `PlayerPlugin.setReplayTimeSource()`. The method's main parameter is a timer source function handle. The function has to always, when called, return current replay time position in recording. The time position is an absolute value (i.e. not relative to recording start or any other value). The reason for this is to simplify synchronization with external data, that started being recorded e.g. before the main recording started.

Another important aspect of the replay is, whether the replay speed may or may not be different than 100% speed. This is set by calling the `enableScalingReplaySpeed()` call. All source plugins have to call the method, if they are to be replayed, but they don't support speed scaling. In that case, the replay scale is disabled globally. The `PlayerPlugin.replay_speed` (an integer; 100 is regular speed, < 100 slower, > 100 faster speed) has to be calculated into the current position, in case the time source's "parent" enables replay speed scaling (it's of course useless otherwise).

After the replay is started, the timer source is periodically being asked about the current replay position time and all source plugins are told the current value. If the content they replay is too much out-of-sync, they have to re-sync by seeking to correct time position. What "too much" means isn't specified by the PlayerPlugin, because a different time-error is acceptable e.g. for video file (0.5s shouldn't really be a problem), than for an audio stream.



##### Seeking and updating replay position #####

During automatic replay, two standard "operations" are to be supported - stream seeking and and stream position updating. The latter one could be viewed on as a lazy version of the first one - we'll see why in a moment.

The seek operation is performed whenever user moves the replay position slider or clicks on the GPX recorded track (with map tool active). In this case, player plugin tells all source plugins to change current replay position to the user-specified one. The seek is done by calling the `PlayerPlugin.seekReplayPosition()` method.

On the other hand, the `PlayerPlugin.updateReplayPosition()` is called periodically. To be precise - `PlayerPlugin.replayTimer_tick()` is periodically called. This method calls the current replay time source and sets current replay position. Eventually, the `PlayerPlugin.updateReplayPosition()` is called with current position as a parameter. This method then updates basic map canvas markers (like current position marker) and then tells source plugins to also update replay position by calling their `updateReplayToTime` methods.

Source plugins don't have to obey the replay time position update exactly. Only in case that the time parameter received by the `SourcePlugin.updateReplayToTime(time)` is too different from current time position (from perspective of the source plugin), the plugin should call e.g. `seekReplayToTime(time)`. As said before - 'too different' is data- and implementation-specific.

Recording seeking note: in both cases - seeking using slider and clicking the GPX track - the seek isn't immediate, but is performed only after user releases the seeking widget (i.e. when `sliderReleased()` is received by `DockWidget` from the slider widget, or when `ReplayMapTool.canvasReleaseEvent()` is received by map tool). This is to prevent huge amount of seeking - which is a problem for some data types of source plugins. For example, if we were processing each `valueChange()` from the seek slider, user could produce 20 seeks per second by just dragging it - this leads to 20 seek commands for source plugins - and to do 20 seeks in a second on a video file produces significant seek delay.


#### Further Visualization Options ####

Apart from the standard replay scheme it's also possible for source plugins (and the player plugin itself) to place canvas items on the map canvas. However, QGIS only enables one 'controller' of the mouse actions at time. This 'controller' is a so called map tool. For user and developer convenience, a map tool is provided by PlayerPlugin that behaves contextually - depending on what canvas item the user clicks on, the "affected source plugin" executes required action.

PlayerPlugin manages all the QGIS-required map tool operations - it is able to (un)set it's own map tool (implemented in the `ReplayMapTool` class) when `PlayerPlugin.useMapTool()` is called. It reacts on external map tool changes (i.e. when user activates other map tool in QGIS) - see `PlayerPlugin.mapToolChanged()` slot.

The `ReplayMapTool` implementation itself is straight-forward. After user clicks on the map canvas, map tool first calls `PlayerPlugin.onMouseButtonPressed()`. That method in turn calls `onMouseButtonPressed()` method of all sources plugins. If some of the methods processes the message, the mouse click is considered processed and no further action is performed.

Otherwise map tool tries to snap the mouse position on the current recorded GPX track. If this succeeds, further mouse actions (until the mouse button is released) are considered being a 'seek operation' - the current replay position is seeked so that it's as near to the mouse position as possible.


### DockWidget ###

Currently, no special functionality is contained in the DockWidget class - it solely provides implementation of user GUI actions. Mostly, when a GUI action is received, it's forwarded to the PlayerPlugin controller class.


## Source Plugins ##


Source plugins in the player plugin work almost the same way as in the Gather plugin (except for the player-specific functionality). See the GatherPluginDev documentation for more information. For additional information on how to create a new source plugin and what functionality is required/provided by player plugin, see the Creating a source plugin section below.

The following sections describe internals of the "standard" source plugins.

### Audio ###

Alike the gatherer audio source plugin, the player's implementation also consists of two parts - Python and C++ module. The first one provides high-level functionality (mainly finding the correct audio file for current recording and time position), the C++ part handles OGG files' decoding and audio device manipulation.

#### Python part ####

Apart from standard features (GUI initialization, configuration load and save) there are two notable features of the plugin - recording manipulation during replay and replay timer.

Recorded audio files are placed in "Audio" subdirectory of current recording and there's support for more audio files per recording. Each file has to be named in format "%Y-%m-%d_%H-%M-%S" (see `datetime.strptime()` Python method) which specifies starting time of the file. When recording is loaded, all audio files are opened and their length is calculated. List of files - containing filename, start time and length - is stored into `PluginAudio.oggFiles` in the `PluginAudio.loadRecording()` method._

When replay is started and audio replay is enabled, first the `PluginAudio.injectOwnTimesource()` is called. It sets source plugin's own time source for the player plugin (to prevent audio glitches). Time scaling is disabled during audio replay. The `PluginAudio.getReplayPosition()` gets current replay time from the C++ part, by calling its `audio_getCurrentTime()` and recalculating the returned value to an absolute value.

Finally, `AudioPlayer.audio_start()` is called to activate audio device. The correct OGG file is chosen, whenever `PluginAudio.updateReplayToTime()` and `PluginAudio.seekReplayToTime()` are called. Both calls lead to `PluginAudio.loadCorrectOgg()` method which finds the correct item from `PluginAudio.oggFiles` list and calls `PluginAudio.switchToOgg()` method. If the file passed to `PluginAudio.switchToOgg()` is different than the current one being replayed, the current OGG file is closed and the new one is opened and started being decoded. To detect when decoding of OGG file is finished (this is detected to enable fast input file switching), an `AudioQuitter` object (derived from `AudioPlayer.OggReplayCallback`) is provided during `AudioPlayer.audio_initialize()`. The object's `onOggEnded()` method is called when the decoding is finished. That leads to `PluginAudio.onOggEnded()` and finally `PluginAudio.loadCorrectOgg()` method. The following diagram, stripped of not-so-important facts, could clarify the situation a bit:

![http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_dev_audio1.png](http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_dev_audio1.png)

#### C++ part ####

C++ audio player part consists of two logical parts - audio device support and an OGG decoder. They both work independently - only the decoder part fills audio buffers to be played by audio device.

When audio system is initialized (`audio_initialize()`), the audio data replay may be started by `audio_start()` function. The function opens audio device and the `paCallback()` function is then being called by PortAudio libraries, whenever new data need to be filled for the device. The `paCallback()` takes data from the `outputBuffer` samples buffer - if there's some (if there's not enough data, it's filled with zeros to prevent noise being replayed).

OGG decoding works in similar manner - after an OGG file is opened (`ogg_openFile`), it's possible to determine the file's length (`ogg_getLength()`) and/or start decoding (`ogg_startDecoding()`). The decoding itself runs in a separate thread (`decodingThreadFct()`) and it simply continuously decodes OGG file and fills the decoded audio samples into the `samplesBuffer` (and sleeps for a while, if the buffer is filled enough). The decoding is automagically stopped whenever the file is about to be closed with `ogg_closeFile()` function (there isn't a special `ogg_stopDecoding()` function because the current player architecture doesn't need one).


### GPS ###
The `PluginGps` doesn't contain any interesting code - the only thing it currently does is that whenever its `updateReplayToTime()` method is called, it reads current GPS position parameters from the controller `PlayerPlugin` and displays them into a list widget.

### Notes ###

When a recording is loaded, the `PluginNotes` reads Notes/notes.xml file and all note child elements of its root element. Each note element contains a time attribute (when the note was placed) and an optional note string. Each note is "converted" into a canvas item (`NoteMarker`) - the coordinates are calculated from the note time by searching the recorded GPX track. The `NoteMarker` class then shows green cross markers on map canvas, if the note doesn't contain any string, or a blue marker if there is an associated text note.

Whenever `onMouseButtonPressed()` method is called, all note markers are checked, whether the mouse position is placed near one of them. In case of a match, the text of the matching note is shown inside of the `PluginNote`'s tabwidget (or "(no note)" text is displayed if the selected note canvas item doesn't contain a string).



### Photo ###

Photo plugin allows user to associate pictures to recording offline (after recording took place). The plugin consists of three logical parts. The first one is the `PluginPhoto` class, managing all the plugin functionality. When a recording is loaded or new images are added to the current recording, small previews (thumbnails) of photos have to be created - this is provided by the `ThumbnailCache`. Finally, after all image previews are cached, canvas items have to be created to display the photos to the user in a convenient way. The following diagram explains the structure visually:

![http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_dev_photo1.png](http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_dev_photo1.png)

The continuous arrows on the right side of diagram show "uses" relation (e.g. `PhotosCanvasItem` uses `ThumbnailCache` to retrieve thumbnails of contained photos). Non-continuous arrows mean parent-derived class relationship.

#### Loading a recording ####

When a recording is being loaded, `PluginPhoto.reloadThumbnailsCache()` method is called. The method creates a `ThumbnailCache` object for the photos directory ("recording\_path/Photo"), and connects to the `cachingFinished()` signal. After the signal is received, `PluginPhoto.cachingFinished()` is called, which fills the tab widget's list of photos.

The `ThumbnailCache` object creates and holds thumbnails and canvas items of photos placed in directory specified at object's creation. The `ThumbnailCache` creation eventually leads to the `ThumbnailCache.updateCache()` method where contents of photos directory is read, obsolete thumbnail files/canvas items are removed and new are scheduled to be cached. The list of thumbnails yet to be created is held by setting `ThumbnailCache.photoCanvasItems[uncachedFile]` to `None`. After caching is finished, this distionary contains all canvas items objects.

After this initialization, `ThumbnailCache.startCaching()` method is called. The method starts `ThumbnailCreatorThread()`, which goes through the `ThumbnailCache.photoCanvasItems` list and creates necessary thumbnails. After each thumbnail is created, `ThumbnailCreatorThread` emits a `thumbnailCreated` signal - which is captured by `ThumbnailCache.thumbnailCreated()`. This method loads the created thumbnail file and stores it into `ThumbnailCache.thumbnailsPixmaps[fileName]`.
Finally, when all thumbnail files are created and loaded, the `thumbnailingFinished()` signal is emited by `ThumbnailCreatorThread`. The signal leads to call of `ThumbnailCache.thumbnailingFinished` method - which (among other things) further leads to `ThumbnailCache.recreateCanvasItems()` method.

#### Canvas items ####

The `ThumbnailCache.recreateCanvasItems()` method removes all previously existing canvas items, cycles through all loaded thumbnail pixmaps and starts creating new canvas items.
There are two types of canvas items used - both derived from the `ImageViewCanvasItem` class. For each thumbnail pixmap, first a `PhotoCanvasItem` is created. If the canvas item doesn't cover any of the previously created canvas items, it's added to the `ThumbnailCache.photoCanvasItems` hash list. If, however, the new canvas item overlaps with some other canvas items, a new `PhotosCanvasItem` is created (or the existing one used, if the overlapping canvas item was of this type) and the previously-created `PhotoCanvasItem` discarded. `PhotosCanvasItem` is able to hold more than one thumbnail pixmap - and after user clicks on it, it expands and shows all contained pixmaps (see later).

After all canvas items are created, the control returns to QGIS. Whenever the `PluginPhoto.onMouseButtonPressed()` method is called, all canvas items are iterated, and if the mouse position matches one of the items, `onMouseButtonPressed()` of that canvas item object is called. Depending on type of object, action is triggered then.

`PhotoCanvasItem.onMouseButtonPressed()` creates a new `ImageViewer` object, which opens the photo file associated with current canvas item (i.e. not the thumbnail) and shows it in a separate window. The window life ends whenever the canvas item is deleted, or when user closes the window manually (in whatever way the window manager allows it). The following image is an example of single `PhotoCanvasItem`:

![http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_src_photo2.png](http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_src_photo2.png)

`PhotosCanvasItem.onMouseButtonPressed()` may lead to several options. Each `PhotosCanvasItem` canvas item may be in two states:
  * collapsed - only a substitute canvas item is placed on map canvas, representing all the thumbnails stored "inside" of it:
> > ![http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_src_photo3.png](http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_src_photo3.png)
  * expanded - the same as collapsed, plus also all contained thumbnails' canvas items are created (as child `PhotoCanvasItem` objects) and surround the main collapsed item
> > ![http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_src_photo4.png](http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_src_photo4.png)

If the mouse position is inside the "collapsed canvas item", the click either creates additional canvas items for the thumbnails (by calling `PhotosCanvasItem.expandCanvasItem()`) or removes them (`PhotosCanvasItem.deleteChildCanvasItems()`). Otherwise, if the click is outside the collapsed item, all the child thumbnail canvas items are iterated until the "correct" is found - the "standard" `PhotoCanvasItem.onMouseButtonPressed()` is called for it.

#### Other functionality ####

The photo plugin allows user to add new photos after recording took place. To determine time when the photos were taken, EXIF information of the photos is read. Each image is then stored inside the "recording\_path/Photo" directory with name equivalent to the date/time of making (e.g. 2009-03-30\_14-03-35.JPG). After all image files are copied, the thumbnails are reloaded by calling `PluginPhoto.reloadThumbnailsCache()`. It's possible for the user to delete existing photos inside the recording.

The last operation worth mentioning is the re-timing functionality - user is enabled to either temporarily re-time photos, and/or to commit the changes (store the photo files with corrected time=name). When only previewing the changes, `PluginPhoto.reloadThumbnailsCache()` is called - which leads, as already mentioned, to creation of new `ThumbnailCache()` object. The `ThumbnailCache()` also receives the time offset parameter, which is automatically added to real photo time in `ThumbnailCache.createPhotoCanvasItem()` and `ThumbnailCache.createPhotosCanvasItem()` methods.

When committing time changes, all photo files are first moved to a temporary directory, then a new time=filename is calculated (using `offsetFileName()` function) and the file is moved from temporary location back to recording/Photo directory. This way, name collisions are trivially prevented. After all files are renamed, the time offset is reset to zero, and again - `PluginPhoto.reloadThumbnailsCache()` is called.



### Video ###

Video source plugin uses embedded MPlayer as video player (previously, a pure ffmpeg-based implementation was used but was discarded in favor of more reliable MPlayer). A working MPlayer is thus required for the plugin to work. Currently, a QX11EmbedContainer is used to embed the MPlayer window inside the video player window - it shouldn't however be hard to implement this functionality in other way (SMPlayer is an example of embedded MPlayer on windows platform).

The plugin consists of several parts (layers of abstraction):

![http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_dev_video1.png](http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_dev_video1.png)

Though the diagram may suggest that the plugin is overcomplicated, the opposite is correct :-)

The `PluginVideo` class is non-mandatory part of the plugin, of course. In a pretty straight-forward way it allows user to open a recorded video file (user may choose any avi file placed inside "Video" subdirectory of the current recording directory). After the file is chosen, a `VideoPlayerWindow` is created, its method `open()` is called to open the requested file and finally a seek to current replay position is simulated. `updateReplayToTime()` and `seekReplayToTime()` methods of `PluginVideo` are forwareded to the `VideoPlayerWindow` methods with the same name.

`VideoPlayerWindow` window/widget currently contains a embedded `VideoPlayerWidget` and a replay position slider (to simplify seeking for user). The single most important method of the `VideoPlayerWindows` class is the `updatePlayState()`. This method is called whenever video replay is to be started/stopped or the current replay position updated/sought.

The `updatePlayState()` first determines current replay position of the `VideoPlayerWidget` widget, compares it to current replay position of player plugin - and in case they differ more than `VIDEO_OFF_TOLERANCE`, the video inside `VideoPlayerWidget` is forced to be sought to correct position. Also, in case play/stop changed since the last state, the new state is enforced (by calling `VideoPlayerWidget.startReplay()` or `VideoPlayerWidget.stopReplay()`).

Finally, the last component made by us is the `VideoPlayerWidget`. The widget uses pymplayer "library" to start MPlayer and embed it into the own widget - this happens at `openFile()`. Also, several video file parameters (like length, fps etc.) are retrieved at this time - and may be retrieved later by "user". Because of the way MPlayer is controlled (by redirecting it's stdin/out streams), the data are periodically tried to be read from it's stdout stream by `VideoPlayerWidget.handleMplayerData()` method. `VideoPlayerWidget` also keeps the current video play state of the MPlayer (in the `vidPlaying` variable), because it's fairly problematic to retrieve current play/pause state of the MPlayer - without moving the current replay position to the next frame.

## Creating New Source Plugins ##

A source plugin provides an interface for player plugin to replay data from a stored device-depedent format (stored previously by gather-counterpart source plugin).

Source plugin interface is pretty simple and straightforward. To create a source plugin, one has to create a file named Plugin**.py (where** stands for a alphanumeric string) in the SourcePlugins directory of the player plugin. A sample implementation of a plugin is placed in PluginDummy.py distributed with the project.

The file has to contain two things - a factory function and a definition of plugin class. The factory function (`getInstance()`) creates the plugin object and returns it. Most of the time, the method will probably look like the one in PluginDummy.py.


### Plugin object functionality ###

The plugin object has to provide some required functionality in order to work correctly. First of all, the object has to be derived from `QWidget`, as is used in the PP user interface as a configuration tab. The widget is inserted to the tab control automatically and has title based on the object's property "name" (which is also a required).

The pair of methods `loadConfig()` and `saveConfig()` load and save configuration. They receive root element of a XML file which they should use.

When `loadRecording()` and `unloadRecording()` are called, plugin should either load recording from specified directory or unload the current one. The exact path is not implied and depends on where/how data was stored by recording counterpart.

The main functionality of replay plugin is handled by `startReplay()`, `stopReplay()`, `updateReplayToTime()` and `seekReplayToTime()` methods. After the `startReplay()` call, the plugin should start replaying, while not blocking the parent thread. The `stopReplay()` should do the opposite - immediately stop replay.

The `updateReplayToTime()` and `seekReplayToTime()` methods are somewhat special. The `updateReplayToTime()` is called from the controller to notify the source plugin on current replay position. This serves for a simple synchronization so that all replay plugins have +- the same position in recording. It's up on the plugin what to do with the time - however it's suggested that the difference between the received time and real time of replay of plugin's data is kept below some meaningful value (which should be e.g. 0.1-0.5 seconds).

The `seekReplayToTime()` is called whenever user manually tries to change current replay position of the recording (e.g. seeks by moving the current recording position slider in the user interface). Replay plugin should immediately seek recording replay to specified time.

Method `onMouseButtonPressed()` is called when player map tool is active and it receives a mouse press event (receives mouse button, map canvas and layer coordinates of the press). If method returns `False`, other plugins are allowed to handle the event, otherwise the mouse event is considered as processed.


### Controller functionality available to plugins ###

Synchronization is the most important part of replay. However, it's not quite trivial to synchronize different sources of unknown time-precision characteristics. The controller provides plugins a 'standard precision timing' by using a timer to calculate current position in replay - the replay position is then submitted to plugins by calling their `updateReplayToTime()` methods as mentioned above. This timer may not be too accurate and if, for example, audio track was synchronized to this timer, there probably would be many glitches.

Because of that, the controller object (passed to source plugins' constructors) provides two methods to enable plugins to provide a more precise timing and replace the internal timer. The methods are `controller.setReplayTimeSource(source)` and `controller.enableScalingReplaySpeed(source, initPos)`.

Method `setReplayTimeSource(source, initTime)` sets the timer function to the specified one (or the internal, if set to `None`). The specified method is then periodically called (instead of the internal timer) to retrieve timer's value (in seconds, floating point number) of current position in recording. If no timer source is provided, the `initTime` parameter tells the internal controller's timer, what's the current position. Note that if there are more source plugins trying to provide custom timer source, they are all considered to be equally accurate - and thus a random one will be used. Because of that it's not granted, that once the method is called, the specified source is really used. Also note that the method may be called even during active replay (so it's possible to start/stop replay of particular source, depending on state of UI for the specified source plugin).

Method `enableScalingReplaySpeed()` tells the controller whether the current plugin allows scaling of replay speed (e.g. whether it's possible to replay the source plugin's data at 2x the nominal speed). If some of the used source plugins doesn't allow speed scaling, the functionality will be disabled completely. So it's wise to disable the scaling only if there are data stored for the particular source plugin don't allow scaling.