# Installation Guide #

This page describes how to install QGIS Mapper project.

The project consists of two parts: Data capture tool and replay tool. Both of them are implemented as (Python) plugins for [Quantum GIS](http://www.qgis.org/). Prior to downloading the plugins it's recommended to install **qgismapper library** that is responsible for hardware handling (cameras, microfone etc). Without the library it's not possible to do audio/video capture and replay.

The whole installation process can be split into three steps.

## Step 1: Quantum GIS ##

First of all you'll need to have Quantum GIS installed on your computer.

You can get it from the [download page](http://www.qgis.org/en/download.html) either as a binary package or you can compile it from source code.

You should be able to use any version >= 1.0. For better functionality and performance we recommend using the latest version.

## Step 2: qgismapper Library (optional) ##

Installation of this library is optional as it just brings additional value to the plugins.

If you are not interested in audio and video support you can skip this section and go to step 3.

Currently there are no binary packages available so you'll have to compile the library from source.

### Dependencies ###

For compilation you'll need:
  * Subversion
  * CMake
  * Qt4
  * Python
  * SIP
  * PyQt4

Dependencies for optional features:
  * **video capture** - **ffmpeg** libraries and development files (ubuntu packages: libavformat-dev libavdevice-dev libavcodec-dev libavutil-dev libswscale-dev)
  * **audio capture/replay** - PortAudio and OGG Vorbis libraries and development files (ubuntu packages: portaudio19-dev libogg-dev libvorbis-dev)
  * **ladybug2 capture** - dc1394 library and development files (ubuntu package: libdc1394-22-dev)

### Installation ###

  1. Check out source code from Subversion repository:
> `svn checkout http://qgismapper.googlecode.com/svn/trunk/mapper`
  1. Configure the project: create a build directory and run `cmake`
  1. Modify configuration variables (using `cmake-gui` or `ccmake`). Interesting variables:
    * **WITH\_AUDIO** - enable support for audio capture/replay. Default: **OFF**
    * **WITH\_VIDEO** - enable support for video capture. Default: **OFF**
    * **WITH\_LADYBUG** - enable support for Ladybug2 spherical camera. Default: **OFF**
  1. Build and install the project (run `make` and `make install`)



## Step 3: Plugins ##

The last step is to install GatherPlugin and/or PlayerPlugin:
  1. Start Quantum GIS
  1. Open menu Plugins -> Fetch Python Plugins... This will fetch updates for plugins and open Plugin Installer
  1. Select "Repositories" tab in the Plugin Installer dialog and click "Add" button
  1. In newly opened dialog use "QGIS Mapper" as repository name and use following address as URL:
> > ` http://qgismapper.googlecode.com/svn/trunk/plugins/plugins.xml `
  1. After clicking OK the installer will fetch information about this newly added repository
  1. In "Plugins" tab now you should see two new plugins in the list:
    * **Data Gather Plugin**
    * **Data Player Plugin**
  1. Install the plugins and enable them in Plugin Manager (menu Plugins -> Manager Plugins...)