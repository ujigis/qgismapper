# Supported Hardware #

This page summarizes what hardware can be used as data sources when recording.

## GPS ##

Nearly any GPS receiver with data output can be used: there's direct support for NMEA-0183 format and there's a support for data from [GPS daemon](http://gpsd.berlios.de/) (gpsd). It features a long [list of supported devices](http://gpsd.berlios.de/hardware.html) including GPS receivers with proprietary output format (e.g. Garmin binary protocol). Gpsd is not available for Windows platform, but there seem to be some Windows ports.

## Digital compass ##

A compass with NMEA-0183 compliant output can be used to calculate exact bearing. This is useful especially when using video cameras to know precisely how the camera(s) are directed.

## Audio ##

The plugin always uses default input. It's up to user to configure system's audio settings: whether to use front microphone, line in plug or some other input.

## Video ##

The plugin supports any cameras that are recognized by Video4Linux (version 1 or version 2). That means that most of the integrated webcams and USB cameras should work.

Video capture is currently available only on Linux (but should be possible to extend on Windows platform too).

## Digital cameras ##

It's possible to take pictures with any digital camera while recording. The player plugin supports geotagging using the EXIF information from the pictures.

## Ladybug2 ##

From the [Ladybug2 product home page](http://www.ptgrey.com/products/ladybug2/index.asp):

_Ladybug®2 spherical digital video camera system has six 0.8 MP cameras that enable the system to collect video from more than 75% of the full sphere, and an IEEE-1394b interface that allows streaming to disk at 30fps._

There's support for data capture and replay of Ladybug2 streams. Data capture is currently available on Linux only (using dc1394 library).