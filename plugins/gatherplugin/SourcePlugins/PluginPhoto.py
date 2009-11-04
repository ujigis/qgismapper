# -*- coding: utf-8 -*-
#THIS PLUGIN IS CURRENTLY UNUSED AND IS REPLACED BY PLAYER PLUGIN VERSION

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PluginPhoto_ui import Ui_PluginPhoto
import re
import os, shutil
import EXIF

class PluginPhoto(QWidget, Ui_PluginPhoto):	
	def __init__(self, controller, parent=None):
		QWidget.__init__(self, parent)
		self.controller=controller
		
		self.setupUi(self)
		self.name="Photo"
		
		self.autoShoot_check.setChecked(0)
		self.autoShootChecked(0)
		self.autoShoot_check.setEnabled(0)
		
		self.autoShootWhenNonsilent_check.setChecked(1)
		self.takeShot_button.setEnabled(0)
		self.takeShot_button.setText(self.tr("No camera found"))
		
		QObject.connect(self.autoShoot_check, SIGNAL("stateChanged(int)"), self.autoShootChecked)
		QObject.connect(self.addPictures_button, SIGNAL("clicked()"), self.addPictures)
		self.recording=0
		
	def loadConfig(self,  rootElement):
		return
	def saveConfig(self,  rootElement):
		return	
	
	def startRecording(self, dataDirectory):
		self.dataDirectory=dataDirectory+self.name+"/"
		self.recording=1
		
	def pollRecording(self):
		pass
		
	def stopRecording(self):
		self.recording=0
	
	def autoShootChecked(self,  state):	
		isChecked=self.autoShoot_check.isChecked()
		self.autoShootEach_check.setEnabled(isChecked)
		self.autoshootEach_edit.setEnabled(isChecked)
		self.autoShootEach_label.setEnabled(isChecked)
		self.autoShootWhenNonsilent_check.setEnabled(isChecked)
	
	def addPictures(self):
		"""
			Add already taken pictures to recording. If no recording is ongoing,
			ask user what data directory he wants to put the photos into.
		"""
		if self.recording==1:
			dir=self.dataDirectory
		else:
			dir=self.controller.getLastDataSubdirectory(self.controller.output_directory)
			dir=str(QFileDialog.getExistingDirectory(self, self.tr("Choose recording session directory"), dir, QFileDialog.ShowDirsOnly))
			if dir=="":
				return
			
		#append self.name, if required
		s=dir.rstrip('/').split('/')
		if len(s) and s[-1]!=self.name:
			dir+=self.name+"/"
		
		if dir[-1]!='/':
			dir+="/"
			
		if not os.path.exists(dir):
			os.makedirs(dir)
		
		files=[str(s) for s in
			QFileDialog.getOpenFileNames(
				self,
				self.tr("Choose images to be added to the photo directory"),
				os.path.expanduser("~"),
				self.tr("Photos (*.jpg *.jpeg)")
			)
		]
		
		for f in files:
			fh=open(f, "rb")
			exif=EXIF.process_file(fh)
			fh.close()
			
			newfn=dir+str(exif["Image DateTime"]).replace(":", "-").replace(" ", "_")+f[f.rfind("."):]
			shutil.copy2(f, newfn)
	
def getInstance(controller):
	return None #PluginPhoto(controller)

