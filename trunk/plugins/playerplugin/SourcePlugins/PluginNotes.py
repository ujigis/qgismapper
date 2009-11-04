# -*- coding: utf-8 -*-
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtXml import *
from qgis.core import *
from qgis.gui import *
from PluginNotes_ui import Ui_PluginNotes
from datetime import datetime
from time import mktime
import os

def QXmlGetNodeStr(node):
	return str(node.firstChild().toText().data()).strip()
def QXmlGetAttr(node, attr):
	return str(node.attributes().namedItem(attr).toAttr().value())

def notedateToUnixTime(timeStr):
	t=datetime.strptime(timeStr, "%Y-%m-%d_%H-%M-%S")
	return mktime(t.timetuple())+1e-6*t.microsecond
	
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
			p.setPen(QColor(0,255,0))
		else:
			p.setPen(QColor(0,128,192))
			
		p.drawLine(-5,-5,5,5)
		p.drawLine(5,-5,-5,5)

class PluginNotes(QWidget, Ui_PluginNotes):
	def __init__(self, controller, parent=None):
		QWidget.__init__(self, parent)
		self.parent=parent
		self.controller=controller
		self.setupUi(self)
		self.name="Notes"
		self.markers=[]
		
	def loadConfig(self, rootElement):
		pass
	def saveConfig(self, rootElement):
		pass
	
	def loadRecording(self, dataDirectory):
		self.setEnabled(0)
		self.dataDirectory=dataDirectory+self.name+"/"
		
		#read the data file
		self.dataFile=self.dataDirectory+"notes.xml"
		self.setEnabled(os.path.isfile(self.dataFile))
		
		if self.markers!=[]:
			self.deleteMarkers()
			
		self.markers=[]
		if not os.path.isfile(self.dataFile):
			return
			
		dom=QDomDocument()
		dom.setContent(open(self.dataFile).read())
		node = dom.documentElement()
		
		#go thru found notes and create notes' canvas items (NoteMarker objects)
		elements=node.elementsByTagName("note")
		for e in range(0, elements.count()):
			element=elements.item(e).toElement()
			time=notedateToUnixTime(QXmlGetAttr(element, "time"))
			note=QXmlGetNodeStr(element)
			if note.strip()=="":
				note=None
			
			item=NoteMarker(
				self.controller.iface.mapCanvas(),
				time,
				note
			)

			item.newCoords(
				self.controller.gpxFile.getTrkPtAtIndex(
					self.controller.gpxFile.getTrkPtAtTime(time)
				).getQGisCoords()
			)
			self.markers.append(item)
			
	def unloadRecording(self):
		self.deleteMarkers()
		self.setEnabled(False)
	
	def startReplay(self, fromTime):
		return
	def stopReplay(self):
		return
		
	def updateReplayToTime(self, time):
		pass
		
	def seekReplayToTime(self, time):
		pass
		
	def onMouseButtonPressed(self, button, canvasPoint, recordingLayerPoint):
		for f in self.markers:
			if f.isPointInside(recordingLayerPoint):
				if f.note!=None:
					self.note_label.setText(f.note)
					self.controller.setActiveSourceTab(self)
					return True
				else:
					self.note_label.setText("("+self.tr("no note")+")")
					return False
				
		return False
		
	def deleteMarkers(self):
		for m in self.markers:
			self.controller.iface.mapCanvas().scene().removeItem(m)

		self.markers=[]
		
def getInstance(controller):
	return PluginNotes(controller)
