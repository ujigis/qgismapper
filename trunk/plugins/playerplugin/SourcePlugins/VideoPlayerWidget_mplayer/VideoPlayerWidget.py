#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from PyQt4 import Qt
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import pymplayer
import time

class VideoPlayerWidget(QWidget):
	def __init__(self, parent, videoFile=None):
		QWidget.__init__(self, parent)

		self.vboxlayout = QVBoxLayout(self)
		self.vidWid=QX11EmbedContainer()
		self.vboxlayout.addWidget(self.vidWid)
		self.setMinimumSize(300, 200)

		if videoFile!=None:
			self.openFile(videoFile)

		self.mplayer=None
		
	def openFile(self, path):
		if self.mplayer!=None:
			self.quit()
		
		self.mplayer=pymplayer.MPlayer()
		self.mplayer.args=["-really-quiet", "-quiet", "-v", "-v", "-v", "-v", "-wid", str(self.vidWid.winId()), "-identify", path]
		self.mplayer.stdout.attach(self.handleMplayerData)
		self.mplayer.stderr.attach(self.handleMplayerData)
		
		self.mplayer.start()
		self.mplayer.command("osd 0")
		self.mplayer.command("pause")

		self.vidLength=0
		self.vidFps=0
		self.vidWidth=0
		self.vidHeight=0
		self.vidPlaying=False
		self.vidCurPos=0

		while True:
			l=self.mplayer.stdout.readline()
			if self.vidLength!=0 or not self.mplayer.is_alive():
				break
			if l!=None:
				self.handleMplayerData(l)
		
		self.startTimer(500)

	def getFrameCount(self):
		l=self.getLength()
		fps=self.getFPS()
		if l and fps:
			return int(float(l)*float(fps))
		else:
			return 0

	def getLength(self):
		return self.vidLength

	def getFPS(self):
		return self.vidFps

	def getCurPos(self):
		return self.vidCurPos

	def handleMplayerData(self, line):
		if line.startswith("ID_VIDEO_WIDTH"):
			self.vidWidth=int(line[line.find("=")+1:])
		elif line.startswith("ID_VIDEO_HEIGHT"):
			self.vidHeight=int(line[line.find("=")+1:])
		elif line.startswith("ID_VIDEO_FPS"):
			self.vidFps=float(line[line.find("=")+1:])
		elif line.startswith("ID_LENGTH"):
			self.vidLength=float(line[line.find("=")+1:])
		elif line.startswith("ANS_TIME_POSITION"):
			self.vidCurPos=float(line[line.find("=")+1:])
			self.emit(SIGNAL("frameDisplayed(int)"), int(self.getCurPos() * self.getFPS()))
		#else:
		#	print "UNHANDLED: ", line

	def seekToTime(self, time):
		self.mplayer.command("pausing_keep seek %f 2" % time)

	def seekToFrame(self, frame):
		self.mplayer.command("pausing_keep seek %f 2" % (frame/self.getFPS()))

	def startReplay(self):
		if self.isPaused():
			self.mplayer.command("pause")
			self.vidPlaying=True

	def stopReplay(self):
		if not self.isPaused():
			self.mplayer.command("pause")
			self.vidPlaying=False

	def quit(self):
		self.mplayer.quit()

	def isPaused(self):
		return not self.vidPlaying
	
	def timerEvent(self, e):
		if not self.isPaused():
			self.mplayer.command("get_time_pos")

			while True:
				l=self.mplayer.stdout.readline()
				if l==None or not self.mplayer.is_alive():
					break
				self.handleMplayerData(l)

	def closeEvent(self, e):
		self.quit()

if __name__ == '__main__':
	class VideoPlayer(QWidget):
		def __init__(self, parent):
			QWidget.__init__(self, parent)
			self.vboxlayout = QVBoxLayout(self)

			self.videoWidget=VideoPlayerWidget(None, sys.argv[1])
			self.vboxlayout.addWidget(self.videoWidget)

			self.hboxlayout= QHBoxLayout()
			self.playStopBtn=QPushButton()
			self.playStopBtn.setText("|>")
			self.hboxlayout.addWidget(self.playStopBtn)

			self.posSlider=QSlider(Qt.Horizontal)
			self.hboxlayout.addWidget(self.posSlider)

			self.vboxlayout.addLayout(self.hboxlayout)

			self.posSlider.setRange(0, self.videoWidget.getFrameCount())

			QObject.connect(self.videoWidget, SIGNAL("frameDisplayed(int)"), self.frameDisplayed)

			QObject.connect(self.posSlider, SIGNAL("actionTriggered(int)"), self.sliderMoved)
			QObject.connect(self.posSlider, SIGNAL("sliderPressed()"), self.sliderPressed)
			QObject.connect(self.posSlider, SIGNAL("sliderReleased()"), self.sliderReleased)

			QObject.connect(self.playStopBtn, SIGNAL("clicked()"), self.playStop)

			self.playing=False
			self.sliderIgnore=False

		def quit(self):
			self.videoWidget.quit()

		def frameDisplayed(self, f):
			self.posSlider.setValue(f)

		def sliderPressed(self):
			self.sliderIgnore=True

		def sliderReleased(self):
			self.sliderIgnore=False
			self.sliderMoved(None)

		def sliderMoved(self, a):
			if self.sliderIgnore:
				return
			self.videoWidget.seekToFrame(self.posSlider.value())

		def playStop(self):
			self.playing=not self.playing
			if self.playing:
				self.videoWidget.startReplay()
			else:
				self.videoWidget.stopReplay()

	a = QApplication(sys.argv)

	mainWidget=MainWidget(None)
	mainWidget.show()

	a.exec_()

	mainWidget.quit()
