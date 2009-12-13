# -*- coding: utf-8 -*-
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from DlgSettings_ui import Ui_DlgSettings

try:
	import gps
	gpsModuleAvailable=True
except:
	gpsModuleAvailable=False

class DlgSettings(QDialog, Ui_DlgSettings):
	def __init__(self, parent=None):
		self.parentDlg=parent
		QDialog.__init__(self, parent)
		self.setupUi(self)
		
		if parent.controller.gps_source == "gpsd" and not gpsModuleAvailable:
			parent.controller.gps_source = "serial"
		
		if parent.controller.gps_source == "serial":
			self.serial_radio.setChecked(1)
		elif parent.controller.gps_source == "file":
			self.file_radio.setChecked(1)
		else:
			self.gpsd_radio.setChecked(1)
		
		self.serial_path.setText(parent.controller.gps_serial)
		self.serial_bauds.setEditText(str(parent.controller.gps_serialBauds))
		
		self.file_path.setText(parent.controller.gps_file)
		self.file_charsPerSecond.setText(str(parent.controller.gps_fileCharsPerSecond))
	
		self.gpsdHost_lineEdit.setText(parent.controller.gps_gpsdHost)
		self.gpsdPort_lineEdit.setText(str(parent.controller.gps_gpsdPort))
		
		if not gpsModuleAvailable:
			self.gpsd_radio.setEnabled(False)
			self.gpsd_radio.setText(self.tr("GPSd not available - missing python gps bindings"))
			self.gpsdHost_lineEdit.setEnabled(False)
			self.gpsdPort_lineEdit.setEnabled(False)

		QObject.connect(self.serial_browse, SIGNAL("clicked()"), self.browseForSerial)
		QObject.connect(self.file_browse, SIGNAL("clicked()"), self.browseForFile)
		QObject.connect(self.btnBrowseInitFile, SIGNAL("clicked()"), self.browseForInitFile)

		for radio in [ self.serial_radio, self.file_radio, self.gpsd_radio ]:
		  QObject.connect(radio, SIGNAL("toggled(bool)"), self.updateGui)
		
		self.serial_bauds.setValidator(QIntValidator(1, 10000000, self.serial_bauds))
		self.file_charsPerSecond.setValidator(QIntValidator(1, 10000000, self.file_charsPerSecond))
		self.gpsdPort_lineEdit.setValidator(QIntValidator(1, 65535, self.gpsdPort_lineEdit))
		
		self.recAttemptCount_spinBox.setValue(parent.controller.gps_attemptsDuringRecording)
		self.reconnectInterval_spinBox.setValue(parent.controller.gps_reconnectInterval)

		if parent.controller.gps_initFile != "":
			self.groupGpsInit.setChecked(True)
			self.editInitFile.setText(parent.controller.gps_initFile)
			
		self.groupCompass.setChecked(parent.controller.compass_use)
		self.editCompassDevice.setText(parent.controller.compass_device)
		self.cboCompassBauds.setEditText(str(parent.controller.compass_bauds))
		self.cboCompassBauds.setValidator(QIntValidator(1, 10000000, self.cboCompassBauds))

		self.updateGui()

	def updateGui(self):
		enabled = self.serial_radio.isChecked()
		self.groupGpsInit.setEnabled(enabled)
		
	def accept(self):
	    
		controller = self.parentDlg.controller
	    
		if self.serial_radio.isChecked():
			controller.gps_source = "serial"
		elif self.file_radio.isChecked():
			controller.gps_source = "file"
		else:
			controller.gps_source = "gpsd"
		controller.gps_serial=str(self.serial_path.text())
		controller.gps_serialBauds=int(self.serial_bauds.currentText())
		controller.gps_file=str(self.file_path.text())
		controller.gps_fileCharsPerSecond=int(self.file_charsPerSecond.text())
		controller.gps_gpsdHost=str(self.gpsdHost_lineEdit.text())
		controller.gps_gpsdPort=int(self.gpsdPort_lineEdit.text())
		
		controller.gps_attemptsDuringRecording=self.recAttemptCount_spinBox.value()
		controller.gps_reconnectInterval=self.reconnectInterval_spinBox.value()
		controller.gps_initFile = str(self.editInitFile.text()) if self.groupGpsInit.isChecked() else ""
		controller.compass_use = self.groupCompass.isChecked()
		controller.compass_device = str(self.editCompassDevice.text())
		controller.compass_bauds = int(self.cboCompassBauds.currentText())
		
		QDialog.accept(self)
	
	def browseForFile(self):
		rv=QFileDialog.getOpenFileName(self, self.tr('Choose a NMEA file'), self.file_path.text(),'*')
		if rv!="":
			self.file_path.setText(rv)
		
	def browseForSerial(self):
		rv=QFileDialog.getOpenFileName(self, self.tr('Choose serial device'), self.serial_path.text(), '*')
		if rv!="":
			self.serial_path.setText(rv)

	def browseForInitFile(self):
		rv=QFileDialog.getOpenFileName(self, self.tr('Choose a file with initialization'), self.editInitFile.text(),'*')
		if rv!="":
			self.editInitFile.setText(rv)
