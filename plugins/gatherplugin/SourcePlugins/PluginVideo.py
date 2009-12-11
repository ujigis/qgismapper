# -*- coding: utf-8 -*-
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PluginVideo_ui import Ui_PluginVideo
from PluginVideo_V4l_ui import Ui_V4LTab_Widget
from qgismapper import PluginVideoWorker
import os, datetime, re

modeRegexp=re.compile("(\d+)x(\d+)[^0-9]*@[^0-9]*(\d+)[^0-9]*")

def parseBool(str):
	return {"True":True, "False":False}[str]

class V4lTab_Widget(QWidget, Ui_V4LTab_Widget):
	def __init__(self, parent, devicePath):
		QWidget.__init__(self, parent)
		self.setupUi(self)
		
		self.setDevice(devicePath)
		self.previewWidget=None
		
		QObject.connect(self.remove_pushButton, SIGNAL("clicked()"), lambda :parent.removeDevice(self))
		QObject.connect(self.modes_comboBox, SIGNAL("editTextChanged(const QString&)"), self.parseNewMode)
		QObject.connect(self.videoPreview_checkBox, SIGNAL("stateChanged(int)"), self.onActivatePreview)
		QObject.connect(parent, SIGNAL("recordingStarted()"), self.connectPreviewToRecording)
		
		self.prevStatus=None
		
	def setDevice(self, device):
		self.device=device
		
		self.fillDialog()
		
	def fillDialog(self):
		self.filename_groupBox.setTitle(self.device)
		
		cap=PluginVideoWorker.getDeviceCapabilities(self.device)
		for mode in cap.modes:
			self.modes_comboBox.addItem(str(mode.width)+"x"+str(mode.height)+" @ "+str(mode.fps)+"fps")
		self.curMode=self.getCurrentModeStr()
		self.isV4l2=cap.v4l2
		
	def getCurrentModeStr(self):
		return str(self.modes_comboBox.currentText())
		
	def getConfiguration(self):
		modeStr=self.getCurrentModeStr()
		mode=modeRegexp.match(modeStr).groups()
		rv=PluginVideoWorker.RecordingParameters("", "mpeg4", 800, self.device, int(mode[0]), int(mode[1]), int(mode[2]), self.isV4l2)
		return rv
	
	def setMode(self, text):
		if modeRegexp.match(text)!=None:
			idx=self.modes_comboBox.findText(text, Qt.MatchStartsWith)
			if idx==-1:
				self.modes_comboBox.lineEdit().setText(text)
				self.curMode=text
			else:
				self.modes_comboBox.setCurrentIndex(idx)
		
	def parseNewMode(self, text):
		if modeRegexp.match(str(text))==None:
			self.modes_comboBox.lineEdit().setText(self.curMode)
		else:
			self.curMode=self.getCurrentModeStr()
			if self.isPreviewActive():
				self.onActivatePreview(False)
				self.onActivatePreview(True)
			
	def onActivatePreview(self, val):
		if not val and self.previewWidget!=None:
			self.filename_groupBox.layout().removeWidget(self.previewWidget)
			self.previewWidget.setParent(None)
			self.previewWidget=None
		elif val and (not self.previewWidget):
			self.previewWidget=PluginVideoWorker.VideoPreview()
			self.filename_groupBox.layout().addWidget(self.previewWidget)
		self.connectPreviewToRecording()
	
	def isPreviewActive(self):
		return self.videoPreview_checkBox.isChecked()
		
	def setPreviewActive(self, active):
		self.videoPreview_checkBox.setChecked(active)
		
	def connectPreviewToRecording(self):
		PluginVideoWorker.setPreviewForDevice(self.getConfiguration(), self.previewWidget, 5)
	
	def enableParameterChanging(self, val):
		self.modes_comboBox.setEnabled(val)
		self.remove_pushButton.setEnabled(val)

	def checkRecStatus(self, isRecording):
		status=not isRecording or PluginVideoWorker.isDeviceBeingRecorded(self.device)
		if status!=self.prevStatus:
			changed=True
		else:
			changed=False
		self.prevStatus=status
		return (status, changed)

class PluginVideo(QWidget, Ui_PluginVideo):
	def __init__(self, controller, parent=None):
		QWidget.__init__(self, parent)
		self.controller=controller
		
		self.setupUi(self)
		self.name="Video"
		self.enabledCheckBox=None

		# hide custom device edit widget
		self.label_2.hide()
		self.customDevice_lineEdit.hide()
		self.customDeviceBrowse_pushButton_2.hide()
		self.line.hide()
		
		PluginVideoWorker.initializeVideo()
		self.refreshDeviceList()
		
		self.recStatusPollingTimer=0
	
		QObject.connect(self.addToUsed_pushButton, SIGNAL("clicked()"), self.addToUsed_pushed)
		QObject.connect(self.customDeviceBrowse_pushButton_2, SIGNAL("clicked()"), self.browseForDevice)
		QObject.connect(self.refreshDevices_pushButton, SIGNAL("clicked()"), self.refreshDeviceList)
		
		QObject.connect(
			self.recordingEnabled_button, SIGNAL("clicked()"),
			self.recordingEnabledDisabled
		)
		
		self.codec_comboBox.addItem("mpeg4")
		self.codec_comboBox.addItem("mjpeg")
		self.codec_comboBox.addItem("libtheora")
		self.codec_comboBox.addItem("libschroedinger")
		self.codec_comboBox.addItem("mpeg1video")
		self.codec_comboBox.addItem("mpeg2video")
		self.codec_comboBox.addItem("libxvid")
		self.codec_comboBox.addItem("libx264")
		self.codec_comboBox.addItem("hoffyuv")
		self.codec_comboBox.addItem("wmv1")
		self.codec_comboBox.addItem("wmv2")
	
	def finalizeUI(self):
		self.enabledCheckBox=self.controller.getRecordingEnabledAuxCheckbox(self.name)
		
		QObject.connect(
			self.enabledCheckBox, SIGNAL("stateChanged(int)"),
			self.recordingEnabledDisabledExternal
		)
		self.deviceCountChanged()
		self.recordingEnabledDisabled()
		
	def loadConfig(self, rootElement):
		if not rootElement:
			return
		ludE=rootElement.elementsByTagName("lastUsedDevices")
		if ludE.count()!=0:
			ludE=ludE.item(0).toElement()
			
			elements=ludE.elementsByTagName("device")
			for e in range(0, elements.count()):
				dev=elements.item(e).toElement()
				if PluginVideoWorker.isDevicePresent(str(dev.attribute("path"))):
					devTab=self.addDevice(str(dev.attribute("path")))
					devTab.setMode(str(dev.attribute("mode")))
					devTab.setPreviewActive(parseBool(str(dev.attribute("showPreview"))))
		
		if (rootElement.attribute("recordingEnabled")!=""):
			self.recordingEnabled_button.setChecked(
				int(rootElement.attribute("recordingEnabled"))
			)
			
		if (rootElement.attribute("codec")!=""):
			self.codec_comboBox.lineEdit().setText(rootElement.attribute("codec"))
		
		if (rootElement.attribute("bitrate")!=""):
			self.codecBitrate_spinBox.setValue(int(rootElement.attribute("bitrate")))
		
	def saveConfig(self, rootElement):
		doc=rootElement.ownerDocument()
		lastUsedDevices=doc.createElement("lastUsedDevices")
		for tabI in self.getVideoTabIndexes():
			tab=self.settings_tabWidget.widget(tabI)
			if PluginVideoWorker.isDevicePresent(str(tab.device)):
				xDev=doc.createElement("device")
				xDev.setAttribute("path", str(tab.device))
				xDev.setAttribute("mode", str(tab.getCurrentModeStr()))
				xDev.setAttribute("showPreview", str(tab.isPreviewActive()))
				
				lastUsedDevices.appendChild(xDev)
		rootElement.appendChild(lastUsedDevices)
		
		rootElement.setAttribute("recordingEnabled",
			str(int(self.recordingEnabled_button.isChecked()))
		)
		
		rootElement.setAttribute("codec", self.getCurrentCodec())
		
		rootElement.setAttribute("bitrate", str(self.getCurrentKBitrate()))
		
	def startRecording(self, dataDirectory):
		self.setParameterChangingUIEnabled(0)
		
		if not self.recordingEnabled_button.isChecked():
			return
			
		self.dataDirectory=dataDirectory+self.name+"/"
		if not os.path.isdir(self.dataDirectory):
			os.mkdir(self.dataDirectory)
		
		recParams=self.getRecordingParameters(self.dataDirectory, datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"), ".avi")

		PluginVideoWorker.startRecording(recParams)
		#update preview connections
		for tabI in self.getVideoTabIndexes():
			tab=self.settings_tabWidget.widget(tabI)
			tab.onActivatePreview(tab.isPreviewActive())
			

		self.recStatusPollingTimer=self.startTimer(500)

		self.emit(SIGNAL("recordingStarted()"))
		
	def pollRecording(self):
		pass
		
	def stopRecording(self):
		if self.recordingEnabled_button.isChecked():
			PluginVideoWorker.stopRecording()
			if self.recStatusPollingTimer!=0:
				self.killTimer(self.recStatusPollingTimer)
				self.recStatusPollingTimer=0

		self.checkRecStatus(False)

		self.setParameterChangingUIEnabled(1)
	
	def browseForDevice(self):
		rv=QFileDialog.getOpenFileName(self, self.tr('Choose device'),"/dev/",'')
		if rv!="":
			self.customDevice_lineEdit.setText(rv)
			
	def addToUsed_pushed(self):
		dev=self.customDevice_lineEdit.text()
		if dev=="":
			for i in self.availableDevices_listWidget.selectedItems():
				dev=i.text()
		if dev=="":
			QMessageBox.information(self, self.tr("Warning"), self.tr("You have to select a device to add!"))
			return
		
		self.addDevice(str(dev))
	
	def addDevice(self, dev):
		tab=V4lTab_Widget(self, dev)
		self.settings_tabWidget.addTab(tab, dev[dev.rfind("/")+1:])
		self.deviceCountChanged()
		return tab
	
	def removeDevice(self, tab):
		self.settings_tabWidget.removeTab(self.settings_tabWidget.indexOf(tab))
		self.deviceCountChanged()
	
	def deviceCountChanged(self):
		if self.settings_tabWidget.count()==2:
			self.recordingEnabled_button.setText(self.tr("no video device configured"))
			self.recordingEnabled_button.setEnabled(False)
			
			if self.enabledCheckBox!=None:
				self.enabledCheckBox.setEnabled(False)
				self.enabledCheckBox.setText(self.tr("Video recording not available (no devices configured)"))
		else:
			self.recordingEnabled_button.setEnabled(True)
			
			if self.enabledCheckBox!=None:
				self.enabledCheckBox.setEnabled(True)
				devs=[self.settings_tabWidget.widget(tabI).device for tabI in self.getVideoTabIndexes()]
				self.setEnabledCheckBox(devs)
			
			self.recordingEnabledDisabled()

	def recordingEnabledDisabled(self):
		if self.recordingEnabled_button.isChecked():
			p = QPixmap(":/icons/dialog-ok-apply.png")
			self.recordingEnabled_button.setText(self.tr("Recording enabled (click to disable)"))
		else:
			p = QPixmap(":/icons/dialog-cancel.png")
			self.recordingEnabled_button.setText(self.tr("Recording disabled (click to enable)"))
		
		self.recordingEnabled_button.setIconSize(p.size())
		self.recordingEnabled_button.setIcon(QIcon(p))

		if self.enabledCheckBox!=None:
			self.enabledCheckBox.setCheckState(
				[Qt.Unchecked, Qt.Checked][int(self.recordingEnabled_button.isChecked())]
			)
			
	def recordingEnabledDisabledExternal(self, state):
		self.recordingEnabled_button.setChecked(state==Qt.Checked)
		
	def getRecordingParameters(self, dir, date, extension):
		rv=[] #QList(PluginVideoWorker.RecordingParameters)
		for tabI in self.getVideoTabIndexes():
			c=self.settings_tabWidget.widget(tabI).getConfiguration()
			c.outputFile=dir+str(tabI-2)+"-"+date+extension
			c.codec=self.getCurrentCodec()
			c.bitrateInKBits=self.getCurrentKBitrate()
			rv.append(c)
		
		return rv
		
	def refreshDeviceList(self):
		self.availableDevices_listWidget.clear()
		devices=PluginVideoWorker.getDevices()
		
		for d in devices:
			self.availableDevices_listWidget.addItem(d)
	
	def setParameterChangingUIEnabled(self, val):
		#handle recording button
		self.recordingEnabled_button.setEnabled(val)
		self.enabledCheckBox.setEnabled(val)
		if (val):
			self.deviceCountChanged()
		
		self.settings_tabWidget.widget(0).setEnabled(False)
		for tabI in self.getVideoTabIndexes():
			self.settings_tabWidget.widget(tabI).enableParameterChanging(val)
	
	def getCurrentCodec(self):
		return str(self.codec_comboBox.currentText())
		
	def getCurrentKBitrate(self):
		return int(self.codecBitrate_spinBox.value())
		
	def getVideoTabIndexes(self):
		#1st tab - devices; 2nd tab - encoder...
		return range(2, self.settings_tabWidget.count())
	
	def timerEvent(self, event):
		if event.timerId()==self.recStatusPollingTimer:
			self.checkRecStatus(True)
		
	def checkRecStatus(self, isRecording):
		ok=True
		devs=[]
		for tabI in self.getVideoTabIndexes():
			w=self.settings_tabWidget.widget(tabI)
			(status,changed)=w.checkRecStatus(isRecording)
			ok=ok and status
			if status and changed:
				self.settings_tabWidget.setTabText(tabI, w.device+self.tr(" (Recording status: Ok)"))
				devs.append(w.device)
			elif changed:
				self.settings_tabWidget.setTabText(tabI, w.device+self.tr(" (Recording status: ERROR)"))
				devs.append(self.tr("Err:")+w.device+"!")
		
		self.setEnabledCheckBox(devs)
		return ok
	
	def setEnabledCheckBox(self, devs):
		devs = map(lambda x: str(x), devs) # convert QStrings to str
		devs_str = ", ".join(devs)
		self.enabledCheckBox.setText(self.tr("Video recording (using device(s): ")+devs_str+")")
	
def getInstance(controller):
	return PluginVideo(controller)
