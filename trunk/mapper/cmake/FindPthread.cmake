# CMake module to search for win32 pthread library
#
# If it's found it sets PTHREAD_FOUND to TRUE
# and following variables are set:
#    PTHREAD_INCLUDE_DIR
#    PTHREAD_LIBRARY

FIND_PATH (PTHREAD_INCLUDE_DIR pthread.h
  # TODO paths?
)

FIND_LIBRARY(PTHREAD_LIBRARY NAMES pthread)

IF (PTHREAD_INCLUDE_DIR AND PTHREAD_LIBRARY)
  SET (PTHREAD_FOUND TRUE)
ENDIF ()
