# -*- coding: utf-8 -*-
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PluginAudio_ui import Ui_PluginAudio
import os, datetime, time
from qgismapper import AudioPlayer

AUDIO_OFF_TOLERANCE=1

def parseAudioFileNameTime(text):
	text=text[0:text.find('.')]
	t=datetime.datetime.strptime(text, "%Y-%m-%d_%H-%M-%S")
	return time.mktime(t.timetuple())+1e-6*t.microsecond

class AudioQuitter(AudioPlayer.OggReplayCallback):
	def __init__(self):
		AudioPlayer.OggReplayCallback.__init__(self)

	def onOggEnded(self):
		self.emit(SIGNAL("oggEnded()"))

class PluginAudio(QWidget, Ui_PluginAudio):
	"""Ogg audio player source plugin"""
	def __init__(self, controller, parent=None):
		QWidget.__init__(self, parent)
		
		self.controller=controller
		
		self.setupUi(self)
		self.name="Audio"
		
		QObject.connect(
			self.active_checkBox, SIGNAL("stateChanged(int)"),
			self.isActiveChanged
		)
		self.lastTime=0
		self.replayActive=False
		self.ownTimesourceUsed=False

		self.audioQuitter=AudioQuitter()
		QObject.connect(
			self.audioQuitter, SIGNAL("oggEnded()"), self.onOggEnded
		)
		
	def loadConfig(self, rootElement):
		return
		
	def saveConfig(self, rootElement):
		return
	
	def loadRecording(self, dataDirectory):
		self.active_checkBox.setChecked(False)
		
		AudioPlayer.audio_initialize(self.audioQuitter)
		
		#create list of available ogg files in current recording
		self.dataDirectory=dataDirectory+self.name+"/"
		self.setEnabled(os.path.isdir(self.dataDirectory))
		if not os.path.isdir(self.dataDirectory):
			self.oggFiles=[]
			return
		
		self.oggFiles=[[f,parseAudioFileNameTime(f)] for f in os.listdir(self.dataDirectory) if (f[f.rfind('.'):].lower()==".ogg")]
		self.setEnabled(self.oggFiles!=[])
		if self.oggFiles==[]:
			return
		
		for oggFile in self.oggFiles:
			AudioPlayer.ogg_openFile(str(self.dataDirectory+oggFile[0]))
			oggFile.append(AudioPlayer.ogg_getLength())
			AudioPlayer.ogg_closeFile()
		
		self.active_checkBox.setChecked(True)
		
		self.currentFile=None
		self.replayActive=False
		
	def unloadRecording(self):
		self.setEnabled(False)
		self.stopReplay()
		AudioPlayer.audio_terminate()
		
	def startReplay(self, fromTime):
		if not self.active_checkBox.isChecked():
			self.active_checkBox.setEnabled(False)
			return
		
		self.stopReplay()
		self.seekReplayToTime(fromTime)
		if not AudioPlayer.audio_start():
				self.active_checkBox.setChecked(False)
				QMessageBox.critical(None, self.tr("Error"), self.tr("Couldn't start audio replay..."))
		else:
			self.replayActive=True
		self.active_checkBox.setEnabled(False)
		
	def stopReplay(self):
		if self.replayActive:
			AudioPlayer.ogg_closeFile()
			AudioPlayer.audio_stop()
			self.replayActive=False
		
		self.active_checkBox.setEnabled(True)
		
	def updateReplayToTime(self, time, forceSeek=False):
		if self.replayActive:
			needSync=((self.getReplayPosition()-time) > AUDIO_OFF_TOLERANCE)
			newFileLoaded=self.loadCorrectOgg(time)
			
			if newFileLoaded or forceSeek or needSync:
				if self.currentFile!=None:
					AudioPlayer.ogg_seekToTime(time-self.currentFile[1])
		
		self.lastTime=time
		
	def seekReplayToTime(self, time):
		self.updateReplayToTime(time, True)
		
		self.lastRewindTime=time
		self.lastRewindStreamTime=AudioPlayer.audio_getCurrentTime()

	def isActiveChanged(self, checked):
		self.injectOwnTimesource(checked)
		
	def injectOwnTimesource(self, active):
		if self.ownTimesourceUsed==active:
			return
		self.controller.enableScalingReplaySpeed(self.name, not active)
		if active:
			self.controller.setReplayTimeSource(self.getReplayPosition)
		else:
			self.controller.setReplayTimeSource(None, self.controller.gpxFile.getTrkPtAtTime(self.lastTime))
		
		self.ownTimesourceUsed=active
		
	def getReplayPosition(self):
		if self.replayActive:
			cst=AudioPlayer.audio_getCurrentTime()
			
			#workaround for weird portaudio behaviour
			if self.lastRewindStreamTime==0:
				self.lastRewindStreamTime=cst
				
			rv=cst-self.lastRewindStreamTime+self.lastRewindTime
			return rv
		else:
			return self.lastTime
		
	def onMouseButtonPressed(self, button, canvasPoint, recordingLayerPoint):
		return False
		
	def loadCorrectOgg(self, curTime):
		if self.oggFiles==[]:
			return False

		bestOgg=None
		for ogg in self.oggFiles:
			if (ogg[1]<=curTime) and ((ogg[1]+ogg[2])>curTime):
				if (bestOgg==None) or (bestOgg!=None and (ogg[1]>bestOgg[1])):
					bestOgg=ogg
		
		return self.switchToOgg(bestOgg, curTime)
	
	def onOggEnded(self):
		self.loadCorrectOgg(self.getReplayPosition())
	
	def switchToOgg(self, newOgg, onlyIfPlaysUntilTime):
		if (self.currentFile!=newOgg):
			if (self.currentFile!=None):
				AudioPlayer.ogg_closeFile()
			
			if (newOgg!=None):
				AudioPlayer.ogg_openFile(str(self.dataDirectory+newOgg[0]))
				AudioPlayer.ogg_startDecoding()
			
			self.currentFile=newOgg

			return newOgg!=None
		
		return False
		
def getInstance(controller):
	return PluginAudio(controller)
