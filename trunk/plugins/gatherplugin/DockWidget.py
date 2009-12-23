# -*- coding: utf-8 -*-
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from DockWidget_ui import Ui_GatherDockWidget
from DlgSettings import DlgSettings
import os,statvfs
import sys

WARNING_DISK_SPACE_MiB=256
MINIMAL_DISK_SPACE_MiB=50


class DockWidget(QDockWidget, Ui_GatherDockWidget,  object):
	def __init__(self, controller,  parent=None):
		QDockWidget.__init__(self,  parent)
		self.controller=controller
		self.setupUi(self)
		self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
		self.connect(self.settings_button,  SIGNAL("clicked()"), self.showSettings)
		self.connect(self,  SIGNAL("destroy()"),  self.destroy)
		
		self.outputPath_edit.setText(self.controller.output_directory)
		self.previewFollowPosition_checkBox.setChecked(self.controller.preview_followPosition)
		self.previewScale_horizontalSlider.setValue(self.controller.preview_scale)
		self.previewKeepPaths_checkBox.setChecked(self.controller.preview_keepPaths)
		
		QObject.connect(self.outputBrowse_button, SIGNAL("clicked()"), self.browseForOutput)
		QObject.connect(self.startRecording_button, SIGNAL("clicked()"), self.controller.recordingSwitch)
		QObject.connect(self.outputPath_edit,  SIGNAL("textChanged(const QString &)"), self.outputPath_changed)
		QObject.connect(self.previewFollowPosition_checkBox,  SIGNAL("stateChanged(int)"), self.previewFollowPosition_changed)
		QObject.connect(self.previewScale_horizontalSlider,  SIGNAL("actionTriggered(int)"), lambda x:self.previewScale_changed(self.previewScale_horizontalSlider.sliderPosition()))
		QObject.connect(self.previewKeepPaths_checkBox,  SIGNAL("stateChanged(int)"), self.previewKeepPaths_changed)
		
		QObject.connect(self.simple_pushButton, SIGNAL("clicked()"), lambda :self.controller.showInterface(simple=True))

		self.diskFreeSpaceTimer=self.startTimer(1000)
		
	def unload(self):
		self.killTimer(self.diskFreeSpaceTimer)
		return
		
	def browseForOutput(self):
		rv=QFileDialog.getExistingDirectory(self, self.tr("Choose output directory"), self.outputPath_edit.text(), QFileDialog.ShowDirsOnly)
		if rv!="":
			self.outputPath_edit.setText(rv)
			
	def outputPath_changed(self, text):
		self.controller.output_directory=str(text)
	
	def previewFollowPosition_changed(self, state):
		self.controller.preview_followPosition=bool(self.previewFollowPosition_checkBox.isChecked())
		
	def previewKeepPaths_changed(self, state):
		self.controller.preview_keepPaths=bool(self.previewKeepPaths_checkBox.isChecked())
		if not self.controller.preview_keepPaths:
			self.controller.removePathPreviews()
	
	def previewScale_changed(self, value):
		self.controller.preview_scale=value
		self.controller.updateExtent()
		
	def showSettings(self):
		self.settingsDialog=DlgSettings(parent=self)
		
		if self.settingsDialog.exec_()==QDialog.Accepted:
			if not self.controller.gpsDaemon.resetGpsSource():
				QMessageBox.information(self, self.tr("Gps reset"),
					self.tr("Previous GPS opening is in progress. Your changes will"
					"be applied after the previous open operation finishes (successfuly or not).")
				)
				
	def set_recording(self,  val):
		""" Update widget UI according to whether recording is on or off """
		if val==True:
			p = QPixmap(":/icons/media-playback-stop.png")
			self.startRecording_button.setText(self.tr("Recording.... (click to stop)"))
			self.startRecording_button.setChecked(True)
			#self.dataInputPlugins_tabWidget.setEnabled(0)
			self.output_groupBox.setEnabled(0)
			self.settings_button.setEnabled(0)
		else:
			p = QPixmap(":/icons/media-record.png")
			self.startRecording_button.setText(self.tr("Start recording"))
			self.startRecording_button.setChecked(False)
			self.startRecording_button.setChecked(False)
			#self.dataInputPlugins_tabWidget.setEnabled(1)
			self.output_groupBox.setEnabled(1)
			self.settings_button.setEnabled(1)

		self.startRecording_button.setIconSize(p.size())
		self.startRecording_button.setIcon(QIcon(p))
	
	def timerEvent(self, event):
		spaceStr=""
		
		try:
			if sys.platform == 'win32':
				import ctypes
				free_bytes = ctypes.c_ulonglong(0)
				drive = unicode(self.controller.output_directory[0:3])
				ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(drive), None, None, ctypes.pointer(free_bytes))
				space = free_bytes.value / 1024 / 1024
			else:
				stats=os.statvfs(self.controller.output_directory)
				space=stats[statvfs.F_BSIZE]*stats[statvfs.F_BAVAIL]/1024/1024
			if space>2048:
				spaceStr="%.2f GiB" % (space/1024.0)
			else:
				spaceStr="%d MiB" % space
		except:
			space=0
			spaceStr="? MiB"
		
		#indicate if space is too low
		style=""
		if space<WARNING_DISK_SPACE_MiB: 
			style=" style=\"color: red;\""
		spaceStr="<html><body><span"+style+">Free space: "+spaceStr+"</span></body></html>"
		
		self.outputFreeSpace_label.setText(spaceStr)
		if self.controller.dockWidget_simple!=None:
			self.controller.dockWidget_simple.outputFreeSpace_label.setText(spaceStr)
		
		if space<MINIMAL_DISK_SPACE_MiB and self.controller.recording:
			self.controller.recordingStop()
			QMessageBox.information(self,
				self.tr("Warning"),
				self.tr("Recording was terminated due to low disk space (< ")+str(MINIMAL_DISK_SPACE_MiB)+" MiB)...",
				self.tr("Ok")
			)
		
	recording=property(lambda x:0,  set_recording)
	
