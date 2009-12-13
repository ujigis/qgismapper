
SET (LADYBUG_SRCS
  ladybug.cpp
  ladybugstream.cpp
  ladybugimage.cpp
  ladybugthread.cpp
  ladybugwidget.cpp
  ladybugplayerthread.cpp
)

SET (LADYBUG_MOC_HDRS
  ladybug.h
  ladybugthread.h
  ladybugwidget.h
)

QT4_WRAP_CPP(LADYBUG_MOC_SRCS ${LADYBUG_MOC_HDRS})

INCLUDE_DIRECTORIES( ${DC1394_INCLUDE_DIR} )

# library name must not be "ladybug" to avoid conflict
# with resulting python ladybug module...
ADD_LIBRARY(ladybugcore STATIC ${LADYBUG_SRCS} ${LADYBUG_MOC_SRCS})

TARGET_LINK_LIBRARIES(ladybugcore ${QT_QTGUI_LIBRARY})

SUBDIRS (test)


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

IF (WIN32)
  SET (WSOCK32_LIBRARY wsock32)
ENDIF ()


FILE(GLOB ladybug_files_sip python/*.sip)
set(SIP_EXTRA_FILES_DEPEND ${ladybug_files_sip})
ADD_SIP_PYTHON_MODULE(qgismapper.ladybug python/ladybug.sip
  ladybugcore
  ${DC1394_LIBRARY}
  ${QT_QTCORE_LIBRARY}
  ${QT_QTGUI_LIBRARY}
  ${WSOCK32_LIBRARY}
  )
