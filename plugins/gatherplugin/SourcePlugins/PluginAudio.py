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
	
		# populate the input devices combo
		settings = QSettings()
		settings.beginGroup("/plugins/GatherPlugin/Audio")
		defaultDeviceIndex = settings.value("inputDevice", PluginAudioWorker.defaultDeviceIndex()).toInt()[0]
		for device in PluginAudioWorker.devices():
			if device.isInput:
				self.cboInputDevice.addItem( "[%s] %s" % (device.api, device.name), QVariant(device.index))
			if device.index == defaultDeviceIndex:
				self.cboInputDevice.setCurrentIndex( self.cboInputDevice.count()-1 ) # use last added device

		enabled = settings.value("recordingEnabled", QVariant(True)).toBool()
		self.recordingEnabled_button.setChecked(enabled)

	def finalizeUI(self):
		self.enabledCheckBox=self.controller.getRecordingEnabledAuxCheckbox(self.name)
		
		QObject.connect(
			self.enabledCheckBox, SIGNAL("stateChanged(int)"),
			self.recordingEnabledDisabledExternal
		)

		self.recordingEnabledDisabled()
		self.audioStatusTimer=self.startTimer(100)
	
	def unload(self):
		self.killTimer(self.audioStatusTimer)
		
		settings = QSettings()
		settings.beginGroup("/plugins/GatherPlugin/Audio")
		if self.cboInputDevice.currentIndex() >= 0:
			device = self.cboInputDevice.itemData(self.cboInputDevice.currentIndex()).toInt()[0]
			settings.setValue("inputDevice", device)

		enabled = self.recordingEnabled_button.isChecked()
		settings.setValue("recordingEnabled", QVariant(enabled))

		PluginAudioWorker.stopAudio()
		PluginAudioWorker.uninitializeAudio()
		
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

		hasDevices = (self.cboInputDevice.count() != 0)
		if not hasDevices:
			self.recordingEnabled_button.setChecked(False)
			self.recordingEnabled_button.setEnabled(False)
			
		if self.recordingEnabled_button.isChecked():
			p = QPixmap(":/icons/dialog-ok-apply.png")
			self.recordingEnabled_button.setText(self.tr("Recording enabled (click to disable)"))
			device = self.cboInputDevice.itemData(self.cboInputDevice.currentIndex()).toInt()[0]
			PluginAudioWorker.startAudio(device)
			self.cboInputDevice.setEnabled(False)
		else:
			p = QPixmap(":/icons/dialog-cancel.png")
			self.recordingEnabled_button.setText(self.tr("Recording disabled (click to enable)") if hasDevices else self.tr("No input devices available"))
			PluginAudioWorker.stopAudio()
			self.cboInputDevice.setEnabled(True)
		
		self.recordingEnabled_button.setIconSize(p.size())
		self.recordingEnabled_button.setIcon(QIcon(p))

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
