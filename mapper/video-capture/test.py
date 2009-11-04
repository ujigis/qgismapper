#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from PyQt4 import Qt
from PyQt4.QtCore import *
from PyQt4.QtGui import *

import PluginVideoWorker

a = QApplication(sys.argv)

class VideoWidget(QWidget):
	def __init__(self, parent, recParams):
		self.recParams=recParams
		
		QWidget.__init__(self, parent)
		self.vboxlayout = QVBoxLayout(self)
		self.checkBox = QCheckBox(self)
		self.checkBox.setText("Show "+dev)
		self.vboxlayout.addWidget(self.checkBox)

		self.checkBox2 = QCheckBox(self)
		self.checkBox2.setText("Is recorded")
		self.checkBox2.setEnabled(False)
		self.vboxlayout.addWidget(self.checkBox2)

		QObject.connect(self.checkBox, SIGNAL("stateChanged(int)"), self.showWidget)
		self.videoPreview=None

		self.statusPollTimer=self.startTimer(500)
		
	def showWidget(self, show):
		if self.videoPreview:
			PluginVideoWorker.setPreviewForDevice(self.recParams, None, 7)
			self.vboxlayout.removeWidget(self.videoPreview)
			self.videoPreview.setParent(None)
			self.videoPreview=None
		elif show:
			self.videoPreview=PluginVideoWorker.VideoPreview()
			self.vboxlayout.addWidget(self.videoPreview)
			PluginVideoWorker.setPreviewForDevice(self.recParams, self.videoPreview, 7)

	def timerEvent(self, event):
		if event.timerId()==self.statusPollTimer:
			self.checkBox2.setChecked(PluginVideoWorker.isDeviceBeingRecorded(self.recParams.device))

class MainWidget(QWidget):
	def __init__(self, parent):
		QWidget.__init__(self, parent)
		self.vboxlayout = QVBoxLayout(self)
		self.checkBox = QCheckBox(self)
		self.checkBox.setText("Recording")
		self.vboxlayout.addWidget(self.checkBox)
		QObject.connect(self.checkBox, SIGNAL("stateChanged(int)"), self.startStopRecording)
		
	def addWidget(self, w):
		self.vboxlayout.addWidget(w)
		
	def setRecordingParams(self, rp):
		self.rp=rp
		
	def startStopRecording(self, start):
		if start:
			PluginVideoWorker.startRecording(self.rp)
			#here we would need to restart previews (for scenario recordingOn+previewOn+recordingOff+recordingOn)
		else:
			PluginVideoWorker.stopRecording()

	def closeEvent(self, event):
		PluginVideoWorker.stopRecording()
		event.accept()
	
PluginVideoWorker.initializeVideo()

if len(sys.argv)==1:
	devIdxs=[0]
else:
	if sys.argv[1]=="list":
		for dev in PluginVideoWorker.getDevices():
			print dev, ":", 
			devCap=PluginVideoWorker.getDeviceCapabilities(dev)
			
			for mod in devCap.modes:
				print mod.width, mod.height, "@", mod.fps, ";",
			print
			
		PluginVideoWorker.uninitializeVideo()
		exit()
	else:
		devIdxs=[int(x) for x in sys.argv[1:]]

mainWidget=MainWidget(None)

rp=[]
pw=[]

for devIdx in devIdxs:
	dev=PluginVideoWorker.getDevices()[devIdx]

	devCap=PluginVideoWorker.getDeviceCapabilities(dev)
	m=devCap.modes[0]
	
	rps=PluginVideoWorker.RecordingParameters("test"+str(devIdx)+".avi", "mpeg4", 800, dev, m.width, m.height, m.fps, devCap.v4l2)
	rp.append(rps)

	w=VideoWidget(None, rps)
	mainWidget.addWidget(w)
	pw.append(w)

mainWidget.setRecordingParams(rp)
mainWidget.show()

a.exec_()

