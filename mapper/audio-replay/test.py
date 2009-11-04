#!/usr/bin/python
# -*- coding: utf-8 -*-

import AudioPlayer
import time, sys
from PyQt4.QtCore import *
from PyQt4.QtGui import *

class Quitter(AudioPlayer.OggReplayCallback, QObject):
	def __init__(self):
		QObject.__init__(self)
		AudioPlayer.OggReplayCallback.__init__(self)
		
	def onOggEnded(self):
		print "end"
		AudioPlayer.audio_stop()
		AudioPlayer.ogg_closeFile()
		AudioPlayer.audio_terminate()
		sys.exit()

q=Quitter()

print AudioPlayer.audio_initialize(q)
AudioPlayer.audio_start()

AudioPlayer.ogg_openFile("test.ogg")
print AudioPlayer.ogg_getLength()
AudioPlayer.ogg_startDecoding()
time.sleep(2)
print "STOP"
AudioPlayer.audio_stop()
print "SLEEP"
time.sleep(2)
print "RESTART"
AudioPlayer.audio_start()
