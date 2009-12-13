# -*- coding: utf-8 -*-
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from VideoPlayerWidget_mplayer import *
from PluginVideo_ui import Ui_PluginVideo
from PluginVideo_playerWindow_ui import Ui_VideoPlayerWindow
import os, datetime, time

def parseVideoFileNameTime(text):
	"""Convert video file name to pair of camera number and time."""
	camNo=text[:text.find('-')]
	text=text[text.find('-')+1:]
	text=text[0:text.find('.')]
	t=datetime.datetime.strptime(text, "%Y-%m-%d_%H-%M-%S")
	return (camNo, time.mktime(t.timetuple())+1e-6*t.microsecond)

VIDEO_OFF_TOLERANCE=1 #seconds

class VideoPlayerWindow(QWidget, Ui_VideoPlayerWindow):
	"""A simple video player window"""
	def __init__(self, parent, controller):
		QWidget.__init__(self, parent, Qt.WindowStaysOnTopHint)
		self.setupUi(self)
		self.controller=controller
		
		QObject.connect(self.videoView, SIGNAL("frameDisplayed(int)"), self.onFrameDisplayed)
		
		QObject.connect(self.videoPosition_slider,
			SIGNAL("actionTriggered(int)"),
			self.videoPosition_sliderMoved
		)

		QObject.connect(self.videoPosition_slider, SIGNAL("sliderPressed()"), self.videoPosition_sliderPressed)
		QObject.connect(self.videoPosition_slider, SIGNAL("sliderReleased()"), self.videoPosition_sliderReleased)
		
		self.__initialize()

	def __initialize(self):
		"""Initialize widget to default state"""
		self.doPlay=False
		self.previousDoPlay=False
		self.playTime=0
		self.videoStartTime=0
		self.videoInvFPS=0
		
		self.ignoreSlider=False
		
	def open(self, path):
		"""Open the specified video file"""
		self.__initialize()
		
		self.videoView.openFile(path)
		self.videoPosition_slider.setRange(0, self.videoView.getFrameCount()-1)
		self.videoPosition_slider.setValue(0)
		self.setWindowTitle(path[path.rfind('/')+1:])	
		(cam, self.videoStartTime)=parseVideoFileNameTime(path[path.rfind("/")+1:])
		self.videoDuration=self.videoView.getLength()
		
		if self.videoView.getFPS()!=0:
			self.videoInvFPS=1/self.videoView.getFPS()
		else:
			self.videoInvFPS=0
		
	def onFrameDisplayed(self, f):
		"""Handle new frame displayed"""
		self.videoPosition_slider.setValue(f)

	def seekReplayToTime(self, time):
		"""Seek current replay position to specified time"""
		self.playTime=time
		self.updatePlayState(True)
		
	def updateReplayToTime(self, time):
		"""Update current replay position to specified time"""
		self.playTime=time
		self.updatePlayState()
		
	def startReplay(self):
		"""Start video file replay"""
		self.doPlay=True
		self.updatePlayState()
		
	def stopReplay(self):
		"""Stop video file replay"""
		self.doPlay=False
		self.updatePlayState()
		
	def updatePlayState(self, forceSeek=False):
		"""
		Update current video player state by seeking current position, and
		starting/stopping replay, if anything of that is needed...
		"""
		
		curVideoTime=self.playTime-self.videoStartTime
		playTimeDiff=curVideoTime-self.videoPosition_slider.value()*self.videoInvFPS
		positionOk=(curVideoTime>=0) and (curVideoTime<self.videoDuration)
		
		if forceSeek or playTimeDiff>VIDEO_OFF_TOLERANCE:
			if positionOk:
				self.videoView.seekToTime(curVideoTime)
				
		if positionOk:
			if self.doPlay!=self.previousDoPlay:
				if self.doPlay:
					self.videoView.startReplay()
				else:
					self.videoView.stopReplay()
				self.previousDoPlay=self.doPlay

		if not self.doPlay:
			self.videoPosition_slider.setValue(int(curVideoTime/self.videoView.getLength()*self.videoPosition_slider.maximum()))

	def videoPosition_sliderMoved(self, action):
		if self.ignoreSlider:
			return
		
		self.controller.seekReplayPosition(
			self.controller.gpxFile.getTrkPtAtTime(self.videoStartTime+self.videoPosition_slider.value()*self.videoInvFPS)
		)
	
	def videoPosition_sliderPressed(self):
		self.ignoreSlider=True
		self.videoPosition_sliderMoved(None)

	def videoPosition_sliderReleased(self):
		self.ignoreSlider=False
		self.videoPosition_sliderMoved(None)

	def doClose(self):
		"""Handle window destroying"""
		self.videoView.close()
	
	def closeEvent(self, event):
		"""Respond to system close event (by only hiding the window)"""
		self.hide()
		event.ignore()

class PluginVideo(QWidget, Ui_PluginVideo):
	def __init__(self, controller, parent=None):
		QWidget.__init__(self, parent)
		self.controller=controller
		
		self.setupUi(self)
		self.name="Video"
		
		self.playerWindow=None
		self.replayActive=False
		
		self.connect(self.records_comboBox, SIGNAL("currentIndexChanged(int)"), lambda f:self.openRecording(f))
		QObject.connect(self.active_checkBox, SIGNAL("stateChanged(int)"), self.isActiveChanged)
		
	def loadRecording(self, dataDirectory):
		self.records_comboBox.clear()
		
		self.dataDirectory=dataDirectory+self.name+"/"
		self.setEnabled(os.path.isdir(self.dataDirectory))
		if not os.path.isdir(self.dataDirectory):
			self.aviFiles=[]
			return
		
		#get list of all contained video files
		self.aviFiles=[[f,parseVideoFileNameTime(f)] for f in os.listdir(self.dataDirectory) if (f[f.rfind('.'):].lower()==".avi")]
		self.setEnabled(self.aviFiles!=[])
		if self.aviFiles==[]:
			return
		
		for f in self.aviFiles:
			#f.append(getVideoLength(str(self.dataDirectory+file[0])))
			self.records_comboBox.addItem(self.tr("Camera ")+str(f[1][0])+self.tr(" (file ")+f[0]+")")
		
		self.active_checkBox.setChecked(True)
		
		self.currentFile=None
		self.replayActive=False
		
		self.setEnabled(True)
		
		self.records_comboBox.setCurrentIndex(0)
	
	def unloadRecording(self):
		self.closePlayerWindow()
		self.stopReplay()
		self.setEnabled(False)
		
	def startReplay(self, fromTime):
		if not self.active_checkBox.isChecked():
			return
			
		self.stopReplay()
		self.seekReplayToTime(fromTime)
		if self.playerWindow:
			self.playerWindow.startReplay()
		self.replayActive=True
		
	def stopReplay(self):
		if self.replayActive:
			if self.playerWindow:
				self.playerWindow.stopReplay()
			self.replayActive=False
		
	def updateReplayToTime(self, time):
		if self.playerWindow:
			self.playerWindow.updateReplayToTime(time)
		
	def seekReplayToTime(self, time):
		#print time
		if self.playerWindow:
			self.playerWindow.seekReplayToTime(time)
		
	def onMouseButtonPressed(self, button, canvasPoint, recordingLayerPoint):
		return False
	
	def isActiveChanged(self, checked):
		if checked:
			self.openRecording(self.records_comboBox.currentIndex())
		else:
			self.openRecording(None)
	
	def openRecording(self, what):
		"""
		Open/close video player window, depending on what file is to be shown.
		
		@param what index of file to be shown; None if no file is to be shown
		"""
		
		#self.closePlayerWindow()
		
		if not self.active_checkBox.isChecked() or what==None or what==-1:
			if self.playerWindow!=None:
				self.playerWindow.hide()
			return
		
		#create new video player window and open the video file inside of it
		if self.playerWindow==None:
			self.playerWindow=VideoPlayerWindow(None, self.controller)
		
		self.playerWindow.open(self.dataDirectory+self.aviFiles[what][0])
		self.playerWindow.show()
		
		#seek the player's video to current replay position
		self.seekReplayToTime(
			self.controller.gpxFile.getTrkPtAtIndex(self.controller.getCurrentReplayPos()).time
		)
		
		#start (automatic) video replay, if replay's currently on
		if self.replayActive:
			self.playerWindow.startReplay()

	def closePlayerWindow(self):
		#close previous video player window
		if self.playerWindow!=None:
			self.playerWindow.doClose()
			self.playerWindow.destroy()
			self.playerWindow=None
			
def getInstance(controller):
	return PluginVideo(controller)
