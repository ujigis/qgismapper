
PROJECT(qgismapper)

CMAKE_MINIMUM_REQUIRED(VERSION 2.6)

SET(CMAKE_MODULE_PATH ${CMAKE_SOURCE_DIR}/cmake)

SET(WITH_AUDIO FALSE CACHE BOOL "Compile support for audio recording/replay")

SET(WITH_VIDEO FALSE CACHE BOOL "Compile support for video recording/replay")

SET(WITH_LADYBUG FALSE CACHE BOOL "Compile support for Ladybug2 camera")


IF (WITH_AUDIO)
  IF (WIN32)
    FIND_PACKAGE(Pthread REQUIRED)
    IF (NOT PTHREAD_FOUND)
      MESSAGE(FATAL_ERROR "Pthreads for win32 is missing! (for audio)")
    ENDIF ()
  ENDIF ()
  FIND_PACKAGE(Portaudio REQUIRED)
  IF (NOT PORTAUDIO_FOUND)
    MESSAGE(FATAL_ERROR "PortAudio is missing! (for audio)")
  ENDIF ()
  FIND_PACKAGE(Vorbis REQUIRED)
  IF (NOT VORBIS_FOUND)
    MESSAGE(FATAL_ERROR "Vorbis is missing! (for audio)")
  ENDIF ()
  MESSAGE(STATUS "Audio support:    YES")
ELSE ()
  MESSAGE(STATUS "Audio support:    NO")
ENDIF ()

IF (WITH_VIDEO)
  FIND_PACKAGE(FFmpeg REQUIRED)
  IF (NOT FFMPEG_FOUND)
    MESSAGE(FATAL_ERROR "FFMPEG is missing! (for video)")
  ENDIF ()
  MESSAGE(STATUS "Video support:    YES")
ELSE ()
  MESSAGE(STATUS "Video support:    NO")
ENDIF ()

IF (WITH_LADYBUG)
  IF (NOT WIN32)
    FIND_PACKAGE(Dc1394 REQUIRED)
  ENDIF ()
  MESSAGE(STATUS "Ladybug2 support: YES")
ELSE ()
  MESSAGE(STATUS "Ladybug2 support: NO")
ENDIF ()

# python support: check for interpreter, sip, pyqt4
FIND_PACKAGE(PythonInterp REQUIRED)
FIND_PACKAGE(PythonLibrary REQUIRED)
FIND_PACKAGE(SIP REQUIRED)
FIND_PACKAGE(PyQt4 REQUIRED)
INCLUDE(PythonMacros)
INCLUDE(SIPMacros)

# setup SIP variables
separate_arguments(PYQT4_SIP_FLAGS) # convert space separated values to a list
set(SIP_INCLUDES ${PYQT4_SIP_DIR})
set(SIP_CONCAT_PARTS 1) # our bindings are small, one part is enough
set(SIP_EXTRA_OPTIONS ${PYQT4_SIP_FLAGS})

# force static libraries to be built as position independent code
# so that they can be used within (shared) python modules
IF (NOT MSVC)
  ADD_DEFINITIONS(-fPIC)
ENDIF ()

# Qt4
FIND_PACKAGE(Qt4 REQUIRED)
INCLUDE(${QT_USE_FILE})

IF (WITH_LADYBUG)
  SUBDIRS(ladybug)
ENDIF (WITH_LADYBUG)

IF (WITH_VIDEO)
  SUBDIRS(video-capture)
ENDIF ()

IF (WITH_AUDIO)
  SUBDIRS(audio-capture)
  SUBDIRS(audio-replay)
ENDIF ()

# common python routines
SUBDIRS(python)
