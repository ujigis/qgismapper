
SET (VIDEO_SRCS
  PluginVideoWorker.cpp
  VideoPreviewWidget.cpp
  GatherThread.cpp
  CompressThread.cpp
  ProcessThread.cpp
  PreviewThread.cpp
)

SET (VIDEO_MOC_HDRS
  PluginVideoWorker.h
  VideoPreviewWidget.h
  PreviewThread.h
)

QT4_WRAP_CPP(VIDEO_MOC_SRCS ${VIDEO_MOC_HDRS})

INCLUDE_DIRECTORIES( ${FFMPEG_INCLUDE_DIRS} )

ADD_LIBRARY(PluginVideoWorker STATIC ${VIDEO_SRCS} ${VIDEO_MOC_SRCS})

TARGET_LINK_LIBRARIES( PluginVideoWorker ${FFMPEG_LIBRARIES} ${QT_QTGUI_LIBRARY})


#####
# PYTHON

INCLUDE_DIRECTORIES(
    ${PYTHON_INCLUDE_PATH}
    ${SIP_INCLUDE_DIR}
    ${QT_INCLUDE_DIR}
    ${QT_QT_INCLUDE_DIR}
    ${QT_QTCORE_INCLUDE_DIR}

    ${CMAKE_CURRENT_SOURCE_DIR}
)

FILE(GLOB video_capture_files_sip sip/*.sip)
set(SIP_EXTRA_FILES_DEPEND ${video_capture_files_sip})
ADD_SIP_PYTHON_MODULE(qgismapper.PluginVideoWorker sip/PluginVideoWorker.sip PluginVideoWorker ${FFMPEG_LIBRARIES})

