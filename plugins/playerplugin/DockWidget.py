# -*- coding: utf-8 -*-
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from DockWidget_ui import Ui_DockWidget
import re, sys, time, os

def secsToMinsString(val):
	val=int(val)
	m="%02d" % int(val/60)
	s="%02d" % int(val%60)
	return m+":"+s
	
class DockWidget(QDockWidget, Ui_DockWidget,  object):
	def __init__(self, controller,  parent=None):
		QDockWidget.__init__(self,  parent)
		self.controller=controller
		self.setupUi(self)
		self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
		self.connect(self,  SIGNAL("destroy()"),  self.destroy)
		
		self.sourcePath_edit.setText(self.controller.source_directory)
		self.replay_followPosition_checkBox.setChecked(self.controller.replay_followPosition)
		
		self.replaySpeed_spinBox.setRange(1, 10000)
		self.replaySpeed_spinBox.setSingleStep(25)
		self.replaySpeed_spinBox.setValue(self.controller.replay_speed)
		QObject.connect(self.replaySpeed_spinBox, SIGNAL("valueChanged(int)"), self.replaySpeed_valueChanged)
		QObject.connect(self.sourcePath_edit, SIGNAL("textChanged(const QString&)"), self.sourcePath_changed)
		
		QObject.connect(self.sourceBrowse_button, SIGNAL("clicked()"), self.browseForSource)
		QObject.connect(self.sourceLoad_pushButton, SIGNAL("clicked()"), self.controller.loadRecordingsList)
		
		QObject.connect(self.import_pushButton, SIGNAL("clicked()"), self.importNewRecording)
		QObject.connect(self.deleteRecording_pushButton, SIGNAL("clicked()"), lambda :self.deleteRecording(self.getCurrentRecording()))
		
		QObject.connect(self.recordings_listView,  SIGNAL("clicked(QModelIndex)"), self.controller.loadSelectedRecording)
		QObject.connect(self.recordings_listView,  SIGNAL("clicked(QModelIndex)"), lambda: self.deleteRecording_pushButton.setEnabled(self.getCurrentRecording()!=None))
		QObject.connect(self.replayPosition_horizontalSlider, SIGNAL("valueChanged(int)"), self.replayPosition_sliderValueChanged)
		QObject.connect(self.replayPosition_horizontalSlider, SIGNAL("sliderReleased()"), self.replayPosition_sliderMoved)
		QObject.connect(self.replayPosition_horizontalSlider, SIGNAL("actionTriggered(int)"), lambda x:self.replayPosition_sliderMoved())
		QObject.connect(self.replay_followPosition_checkBox,  SIGNAL("stateChanged(int)"), self.replayFollowPosition_changed)
		
		QObject.connect(self.replayPlay_pushButton, SIGNAL("toggled(bool)"), self.replayPlay_toggled)
		QObject.connect(self.replay_mapTool_pushButton, SIGNAL("toggled(bool)"), self.replayMapTool_toggled)
		
		QObject.connect(self.controller, SIGNAL("recordingSwitched()"), self.updateUIForNewRecording)
		self.updateUIForNewRecording()
		
	def unload(self):
		return
		
	def browseForSource(self):
		"""Show directory selecting dialog and set specified path do source path widget"""
		rv=QFileDialog.getExistingDirectory(self, self.tr("Choose data source directory"), self.sourcePath_edit.text(), QFileDialog.ShowDirsOnly)
		if rv!="":
			self.sourcePath_edit.setText(rv)
			
	def sourcePath_changed(self, text):
		"""Handle changing source path by the user."""
		if text=="":
			return
		if (text[len(text)-1]!='/') and (text[len(text)-1]!='\\'):
			text=text+'/'
			self.sourcePath_edit.setText(text)
		self.controller.source_directory=str(text)
		
	def getCurrentRecording(self):
		"""Returns current recording name"""
		model=self.recordings_listView.model()
		for i in self.recordings_listView.selectedIndexes():
			return str(model.data(i, Qt.UserRole).toString())
		return None
		
	def updateUIForNewRecording(self):
		"""Update UI to display parameters of newly loaded recording"""
		loaded=self.controller.isRecordingLoaded()
		self.replay_groupBox.setEnabled(loaded)
		self.dataInputPlugins_tabWidget.setEnabled(loaded)
		if not loaded:
			self.replay_mapTool_pushButton.setChecked(False)
			self.replayPosition_horizontalSlider.setRange(0, 0)
			self.replayPosition_horizontalSlider.setValue(0)
			self.replayPosition_label_4.setText("--:-- / --:--")
			return
		
		self.replayPosition_horizontalSlider.setMinimum(0)
		self.replayPosition_horizontalSlider.setMaximum(self.controller.gpxFile.length-1)
		
		self.replayPosition_horizontalSlider.setValue(0)
		self.replayPosition_sliderValueChanged(0) #in case of change from 0 to 0 :-)
		
		self.replay_mapTool_pushButton.setChecked(True)
		
	def selectNoRecording(self):
		self.recordings_listView.clearSelection()
	
	def replayPosition_sliderValueChanged(self, val):
		"""Handle value change of replay position slider"""
		#tell plugins about the new value
		if not self.controller.isRecordingLoaded():
			return
			
		self.controller.updateReplayPosition(val)
		
		#show new time position
		timepos=self.controller.gpxFile.getTrkPtAtIndex(val).time-self.controller.gpxFile.minTime
		self.replayPosition_label_4.setText(
			secsToMinsString(timepos)+
			"/"+
			secsToMinsString(self.controller.gpxFile.duration)
		)
		
	def replayPosition_sliderMoved(self):
		"""Handle moving of replay position slider by user (rewind current recording pos.)"""
		self.controller.notifySeekReplayPosition(self.replayPosition_horizontalSlider.sliderPosition())
		
	def replayFollowPosition_changed(self, data):
		"""Handle changing "checked" state of replay-follow-position checkbox"""
		self.controller.replay_followPosition=bool(self.replay_followPosition_checkBox.isChecked())
	
	def replaySpeed_valueChanged(self, val):
		"""Handle changing replay speed"""
		self.controller.replay_speed=val
		
	def replayPlay_toggled(self, checked):
		"""Start/stop replay, depending on checked parameter"""
		if checked:
			self.replayPlay_pushButton.setText(self.tr("Stop"))
			self.controller.startReplay(self.replayPosition_horizontalSlider.value())
		else:
			self.replayPlay_pushButton.setText(self.tr("Play"))
			self.controller.stopReplay()
			
	def replayPlay_set(self, checked):
		self.replayPlay_pushButton.setChecked(checked)
		
	def replayMapTool_toggled(self, checked):
		"""Enable/disable replay map tool"""
		self.controller.useMapTool(checked)
	
	def importNewRecording(self):
		"""Show nmea file-choose dialog and tell controller which file to load"""
		nmeaFile=QFileDialog.getOpenFileName(self, self.tr("Choose nmea log file"), os.path.expanduser("~"))
		if nmeaFile=="":
			return
		rvImport=self.controller.importNmeaLog(nmeaFile)
		if rvImport==True:
			self.controller.loadRecordingsList()
			#TODO: select the new recording
			QMessageBox.information(self, self.tr("Information"), self.tr("The import of file ")+nmeaFile+self.tr(" was successful!"))
		else:
			QMessageBox.warning(self, self.tr("Warning"), self.tr("The import of file ")+nmeaFile+self.tr(" was unsuccessful (error:")+str(rvImport)+self.tr(")!"))
			
	def deleteRecording(self, rec):
		"""Ask user, whether to delete specified recording and commit if yes."""
		if QMessageBox.question(self, self.tr("Warning"), self.tr("Really delete the recording (ID ")+rec+self.tr(")?"), QMessageBox.Yes|QMessageBox.No)==QMessageBox.Yes:
			self.controller.deleteRecording(rec)
	
	def enableRecordingsList(self, val):
		"""Enable/disable recordings list and associated controls, depending on val"""
		self.recordings_listView.setEnabled(val)
		self.import_pushButton.setEnabled(val)
		
		if not val:
			self.deleteRecording_pushButton.setEnabled(val)
	
	def setActiveSourceTab(self, widget):
		"""Set the specified widget as the currently active source plugin tab."""
		self.dataInputPlugins_tabWidget.setCurrentWidget(widget)

	def enableScalingReplaySpeed(self, enable):
		"""Enable/disable the speed scaling spinbox"""
		self.replaySpeed_spinBox.setEnabled(enable)
		if not enable:
			self.replaySpeed_spinBox.setValue(100)
	
	def setRecordingsListContents(self, recList):
		"""
		Set contents of the recordings list to specified list. The list items have to
		be in the correct format - see RecordingsDataModel.regex.
		"""
		self.recordings_listView.setModel(
			RecordingsDataModel(recList, self)
		)
		
	def setReplayFollowPositionChecked(self, check):
		"""Set whether the 'follow position' checkbox is checked"""
		self.replay_followPosition_checkBox.setChecked(check)
	
	def setReplayPosition(self, pos, simulateSeek=False):
		"""
		Set current replay position, and if simulateSeek==True, behave as if user
		moved the slider by dragging the slider.
		"""
		self.replayPosition_horizontalSlider.setValue(pos)
		if simulateSeek:
			self.replayPosition_sliderMoved()
	
	def getReplayPosition(self):
		"""Return current replay position"""
		return self.replayPosition_horizontalSlider.value()
	
	def __getMapToolChecked(self):
		return self.replay_mapTool_pushButton.isChecked()
	def __setMapToolChecked(self, val):
		self.replay_mapTool_pushButton.setChecked(val)
	mapToolChecked=property(__getMapToolChecked, __setMapToolChecked)
	"""Get/Set map tool usage checkbox checked value."""
	
class RecordingsDataModel(QAbstractListModel): 
	"""Datamodel for displaying list of recording in list view"""
	regex=re.compile("(\d+)-(\d+)-(\d+)_(\d+)-(\d+)-(\d+)")
	regexReplace=r"\3.\2. \1 - \4:\5:\6"
	
	def __init__(self, listData, parent=None, *args): 
		QAbstractTableModel.__init__(self, parent, *args)
		self.listData=[(d, self.regex.sub(self.regexReplace, d)) for d in listData]
		
	def rowCount(self, parent=QModelIndex()):
		return len(self.listData)
	
	def data(self, index, role):
		if index.isValid() and role == Qt.DisplayRole:
			return QVariant(self.listData[index.row()][1])
		elif index.isValid() and role == Qt.UserRole:
			return QVariant(self.listData[index.row()][0])
		else:
			return QVariant()
