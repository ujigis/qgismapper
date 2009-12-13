# -*- coding: utf-8 -*-
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtXml import *
from PluginNotes_ui import Ui_PluginNotes
import os, datetime
from qgis.core import *
from qgis.gui import *

class NoteMarker(QgsMapCanvasItem):
	def __init__(self, canvas, time, note=None):
		QgsMapCanvasItem.__init__(self, canvas)
		self.time=time
		self.note=note
		
	def newCoords(self, pos):
		if self.pos != pos:
			self.pos = QgsPoint(pos) # copy
			self.updatePosition()
	
	def setHasPosition(self, has):
		if self.hasPosition != has:
			self.hasPosition = has
			self.update()
		
	def updatePosition(self):
		if self.pos:
			self.setPos(self.toCanvasCoordinates(self.pos))
			self.update()
	
	def boundingRect(self):
		return QRectF(-5, -5, 10, 10)
		
	def isPointInside(self, pt):
		#FIXME: we need to convert pt frm layer to map coordinates here
		rect=self.boundingRect()
		rect.moveCenter(self.toCanvasCoordinates(self.pos))
		return rect.contains(self.toCanvasCoordinates(pt))
		
	def paint(self, p, xxx, xxx2):
		if not self.pos:
			return
		
		if self.note==None:
			color = QColor(255,90,0) if self.time is None else QColor(0,255,0)
		else:
			color = QColor(0,128,192)
		p.setPen(QPen(QBrush(color),2))
			
		p.drawLine(-5,-5,5,5)
		p.drawLine(5,-5,-5,5)


class PluginNotes(QWidget, Ui_PluginNotes):
	def __init__(self, controller, parent=None):
		QWidget.__init__(self, parent)
		self.controller=controller
		
		self.setupUi(self)
		self.name="Notes"
		
		QObject.connect(self.mark_button, SIGNAL("clicked()"), self.markCurrentPosition)
		QObject.connect(self.noteAdd_pushButton, SIGNAL("clicked()"), lambda:self.commitMark(True))
		QObject.connect(self.noNote_pushButton, SIGNAL("clicked()"), lambda:self.commitMark(False))
		
		self.setEnabled(False)
		self.canvasItems=[]
		
		self.lastPos=None
		self.lastMark=None
		
	def finalizeUI(self):
		pass
		
	def loadConfig(self, rootElement):
		pass
	def saveConfig(self, rootElement):
		pass
	
	def startRecording(self, dataDirectory):
		self.dataDirectory=dataDirectory+self.name+"/"
		if not os.path.isdir(self.dataDirectory):
			os.mkdir(self.dataDirectory)
		self.notesDoc=QDomDocument()
		self.notesDoc.appendChild(
			self.notesDoc.createProcessingInstruction(
				"xml", "version=\"1.0\" encoding=\"utf-8\""
			)
		)
	
		self.notesRoot=self.notesDoc.createElement("notes")
		self.notesRoot.setAttribute("version",  "1.0")
		self.notesDoc.appendChild(self.notesRoot)
		self.setEnabled(True)
		
	def pollRecording(self):
		pass
		
	def stopRecording(self):
		self.setEnabled(False)
		file=QFile(self.dataDirectory+"notes.xml")
		file.open(QIODevice.WriteOnly)
		file.write(str(self.notesDoc.toString()))
		file.close()
		self.notesDoc=None
	
	def markCurrentPosition(self):
		if self.lastPos!=None:
			self.commitMark(True)
			self.delTempMarkCanvasItem()
		
		pos=self.getCurGPSPosition()
		time=datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
		self.lastPos=(pos, time)
		
		self.addTempMarkCanvasItem(pos)

		self.note_stackedWidget.setCurrentIndex(1)

		# set focus so the user can directly type the note
		self.note_lineEdit.setFocus(Qt.OtherFocusReason)
		
	def commitMark(self, withNote):
		if withNote:
			note=self.note_lineEdit.text()
			if note=="":
				note=None
		else:
			note=None
		
		self.addXmlNote(self.lastPos[1], note)
		self.addNewCanvasItem(self.lastPos[0], self.lastPos[1], note)
		
		self.delTempMarkCanvasItem()
		self.note_lineEdit.setText("")
		self.note_stackedWidget.setCurrentIndex(0)
		self.lastPos=None
		
	def addNewCanvasItem(self, pos, time, note):
		noteItem=NoteMarker(
			self.controller.iface.mapCanvas(),
			time,
			note
		)
		noteItem.newCoords(pos)
		self.canvasItems.append(noteItem)
	
	def addTempMarkCanvasItem(self, pos):
		self.lastMark=NoteMarker(
			self.controller.iface.mapCanvas(),
			None,
			None
		)
		self.lastMark.newCoords(pos)
		
	def delTempMarkCanvasItem(self):
		if self.lastMark!=None:
			self.controller.iface.mapCanvas().scene().removeItem(self.lastMark)
			self.lastMark=None
			
	def addXmlNote(self, time, note=None):
		element=self.notesDoc.createElement("note")
		element.setAttribute("time", time)
		if note:
			element.appendChild(
				self.notesDoc.createTextNode(note)
			)
		
		self.notesRoot.appendChild(element)
	
	def getCurGPSPosition(self):
		try:	
			np=self.controller.getNmeaParser()
			
			if not self.controller.isGpsConnected() or np==None:
				raise Exception('gps error')
		except:
			return None
		
		return QgsPoint(np.lon, np.lat)
		
	def clearMapCanvasItems(self):
		for ci in self.canvasItems:
			self.controller.iface.mapCanvas().scene().removeItem(ci)
			
		self.canvasItems=[]
	
def getInstance(controller):
	return PluginNotes(controller)
