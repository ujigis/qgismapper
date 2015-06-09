# Introduction #

Aim of this project is to help with collection of geographical data in field (i.e. driving a car with GPS) by creating a flexible system that stores collected data from different sources (GPS, microphone, camera). Then, the software will allow viewing the collected data easily and help the user with digitizing process providing effective editing tools and visualization options. As a result, users should get system capable to work with big amounts of geographical data with no need to use other (commercial) GIS software.


The project is available for use by both professional and amateur/hobby mappers. The software supports a variety of hardware devices used for mapping in terrain and can be easily extended to support more devices.

**Professionals** can take advantage of support for multiple video cameras, Ladybug2 spherical camera, geodetic GPS receivers and/or digital compass. All these data sources can be recorded together and later replayed in synchronization.

**Amateurs** who gather data e.g. for [OpenStreetMap](http://www.openstreetmap.org) project can use low-cost equipment: Bluetooth GPS receiver, optionally augmented with video capture from a simple webcam or using pictures taken by a digital camera.

The project makes use of [Quantum GIS](http://www.qgis.org/) (QGIS). It is a piece of software licensed under GNU GPL for visualization and editing of geographical data. Its libraries allow 3rd party software to load, read and display geographical data. QGIS can be extended by plugins in either C++ and Python.

# Documentation #

  * SupportedHardware - devices that can be used for recording
  * InstallationGuide - how to install QGIS Mapper
  * GatherPlugin - how to capture data
  * PlayerPlugin - how to replay data

Developer documentation:
  * GatherPluginDev
  * PlayerPluginDev

An example of a car for data capture equipped with Ladybug2 spherical camera and running QGIS Mapper software:

![http://qgismapper.googlecode.com/svn/trunk/doc/car_photo.jpg](http://qgismapper.googlecode.com/svn/trunk/doc/car_photo.jpg)

# Screenshot #

![http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_recording.png](http://qgismapper.googlecode.com/svn/trunk/doc/playerplugin/player_recording.png)