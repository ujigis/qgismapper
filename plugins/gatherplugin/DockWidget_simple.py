# -*- coding: utf-8 -*-
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from DockWidget_simple_ui import Ui_DockWidget_simple

class DockWidget_simple(QDockWidget, Ui_DockWidget_simple,  object):
	def __init__(self, controller,  parent=None):
		QDockWidget.__init__(self,  parent)
		self.controller=controller
		self.setupUi(self)
		self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
		self.connect(self,  SIGNAL("destroy()"),  self.destroy)
		
		QObject.connect(self.startRecording_button, SIGNAL("clicked()"), self.controller.recordingSwitch)
		QObject.connect(self.full_pushButton, SIGNAL("clicked()"), lambda :self.controller.showInterface(simple=False))
		
	def unload(self):
		return
			
	def set_recording(self,  val):
		""" Update widget UI according to whether recording is on or off """
		if val==True:
			self.startRecording_button.setText("Recording.... (click to stop)")
			self.startRecording_button.setChecked(True)
		else:
			self.startRecording_button.setText("Start recording")
			self.startRecording_button.setChecked(False)
	recording=property(lambda x:0,  set_recording)

	def getRecordingEnabledCheckbox(self, source):
		if source=="Audio":
			return self.audio_checkBox
		elif source=="Video":
			return self.video_checkBox
		elif source=="Gps":
			return (self.gps_widget, self.gps_label)
		return None
