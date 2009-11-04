# -*- coding: utf-8 -*-
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
import resources_rc
from CanvasMarkers import *

MaxSnappingDistance=50

class ReplayMapTool(QgsMapToolPan):
	"""
	Map tool that enables user interact with source plugins' canvas items,
	and if no source plugin "is interested", it allows convenient way of current
	recording position seeking by clicking on the recording gpx track on map. If
	the user clicks out of gpx track region, the map tool works as pan map tool.
	"""
	def __init__(self, canvas, controller):
		QgsMapToolPan.__init__(self, canvas)
		self.controller=controller
		self.posMarker=None
		self.rewinding=False
		
	def canvasPressEvent(self, mouseEvent):
		layerPt=self.canvasPointToRecordingLayerPoint(mouseEvent.pos().x(), mouseEvent.pos().y())
		if self.controller.onMouseButtonPressed(mouseEvent.button(), (mouseEvent.pos().x(), mouseEvent.pos().y()), layerPt):
			#one of the source plugins catched the click, don't continue any further
			return
			
		if mouseEvent.button()==Qt.LeftButton:
			if self.trySnappingPosition(mouseEvent.pos().x(), mouseEvent.pos().y()):
				#click on the recorded track
				self.rewinding=True
			else:
				#otherwise use the qgis pan map tool
				QgsMapToolPan.canvasPressEvent(self, mouseEvent)
		
	def canvasMoveEvent(self, mouseEvent):
		if mouseEvent.buttons()&Qt.LeftButton and self.rewinding:
			if not self.trySnappingPosition(mouseEvent.pos().x(), mouseEvent.pos().y()):
				QgsMapToolPan.canvasMoveEvent(self, mouseEvent)
		else:
			QgsMapToolPan.canvasMoveEvent(self, mouseEvent)
		
	def canvasReleaseEvent(self, mouseEvent):
		if mouseEvent.button()&Qt.LeftButton and self.rewinding:
			#We were showing user target replay position, now do the real seek in recording
			#and discard the temporary canvas item
			self.trySnappingPosition(mouseEvent.pos().x(), mouseEvent.pos().y(), True)
			self.rewinding=False
			
			self.canvas().scene().removeItem(self.posMarker)
			self.posMarker=None
			
		QgsMapToolPan.canvasReleaseEvent(self, mouseEvent)
		
	def trySnappingPosition(self, x, y, doSeek=False):
		"""
		Try snapping the specified position to recorded track, and start displaying
		target seek postion/do the seek, depending on doSeek parameter.
		"""
		layerPoint=self.canvasPointToRecordingLayerPoint(x, y)
		
		(recIndex,recPoint)=self.controller.findNearestPointInRecording(layerPoint)
		recPointQgs=QgsPoint(recPoint.lon, recPoint.lat)
		p=self.toCanvasCoordinates(recPointQgs)
		if abs(complex(p.x()-x, p.y()-y))<MaxSnappingDistance:
			#the mouse position snaps to recording, handle it
			if doSeek:
				#either do the seek
				self.controller.seekReplayPosition(recIndex, True)
			else:
				#or start showing temporary seek canvas item
				if self.posMarker == None:
					self.posMarker=PositionMarker(self.canvas(), 128)
				
				self.posMarker.setHasPosition(True)
				self.posMarker.newCoords(recPointQgs)
				self.posMarker.angle=recPoint.angle
		
			return True
		else:
			return False
		
	def canvasPointToRecordingLayerPoint(self, x, y):
		mapPoint = self.canvas().getCoordinateTransform().toMapPoint(x, y)
		return self.canvas().mapRenderer().mapToLayerCoordinates(self.controller.lastRecordingLayer, mapPoint)
