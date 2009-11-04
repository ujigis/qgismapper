# -*- coding: utf-8 -*-
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import os, datetime
from qgismapper import PluginAudioWorker
from PluginAudio_ui import Ui_PluginAudio

class PluginAudio(QWidget, Ui_PluginAudio):
	def __init__(self, controller, parent=None):
		QWidget.__init__(self, parent)
		self.controller=controller
		
		self.setupUi(self)
		self.name="Audio"
		
		self.enabledCheckBox=None

		QObject.connect(
			self.recordingEnabled_button, SIGNAL("clicked()"),
			self.recordingEnabledDisabled
		)
		
		PluginAudioWorker.initializeAudio()
		self.audioStatusTimer=self.startTimer(200)
	
	def finalizeUI(self):
		self.enabledCheckBox=self.controller.getRecordingEnabledAuxCheckbox(self.name)
		
		QObject.connect(
			self.enabledCheckBox, SIGNAL("stateChanged(int)"),
			self.recordingEnabledDisabledExternal
		)
		self.recordingEnabledDisabled()
	
	def unload(self):
		self.killTimer(self.audioStatusTimer)
		
		PluginAudioWorker.stopAudio()
		PluginAudioWorker.uninitializeAudio()
		
	def loadConfig(self, rootElement):
		if not rootElement:
			return
			
		if (rootElement.attribute("recordingEnabled")!=""):
			self.recordingEnabled_button.setChecked(
				int(rootElement.attribute("recordingEnabled"))
			)
		else:
			self.recordingEnabled_button.setChecked(True)
		
	def saveConfig(self, rootElement):
		rootElement.setAttribute("recordingEnabled",
			str(int(self.recordingEnabled_button.isChecked()))
		)
	
	def startRecording(self, dataDirectory):
		self.setEnabled(False)
		self.enabledCheckBox.setEnabled(False)
		
		if not self.recordingEnabled_button.isChecked():
			return
			
		self.dataDirectory=dataDirectory+self.name+"/"
		if not os.path.isdir(self.dataDirectory):
			os.mkdir(self.dataDirectory)
		
		self.outputFile=str(self.dataDirectory+datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")+".ogg")
		PluginAudioWorker.startRecording(self.outputFile)
		
	def pollRecording(self):
		return None
		
	def stopRecording(self):
		if self.recordingEnabled_button.isChecked():
			PluginAudioWorker.stopRecording()
		
		self.enabledCheckBox.setEnabled(True)
		self.setEnabled(True)
		
	def recordingEnabledDisabled(self):
		if self.recordingEnabled_button.isChecked():
			self.recordingEnabled_button.setText(self.tr("Recording enabled (click to disable)"))
			PluginAudioWorker.startAudio()
		else:
			self.recordingEnabled_button.setText(self.tr("Recording disabled (click to enable)"))
			PluginAudioWorker.stopAudio()
		
		if self.enabledCheckBox!=None:
			self.enabledCheckBox.setCheckState(
				[Qt.Unchecked, Qt.Checked][int(self.recordingEnabled_button.isChecked())]
			)
			
	def recordingEnabledDisabledExternal(self, state):
		self.recordingEnabled_button.setChecked(state==Qt.Checked)

	def timerEvent(self, event):
		if event.timerId()==self.audioStatusTimer:
			self.audioStatus.setPeak(PluginAudioWorker.getCapturedAudioPeak())
	
def getInstance(controller):
	return PluginAudio(controller)
