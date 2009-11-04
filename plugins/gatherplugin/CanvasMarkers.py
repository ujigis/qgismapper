# -*- coding: utf-8 -*-

from PyQt4 import QtCore, QtGui
from qgis.core import *
from qgis.gui import *


class RoutePointMarker(QgsMapCanvasItem):
	""" marker for start and end of the route """
	
	Start, Stop = range(2)
	
	def __init__(self, canvas, markerType):
		QgsMapCanvasItem.__init__(self, canvas)
		self.d = 21
		self.pos = None	
		self.markerType = markerType
		self.setZValue(90)
		
	def setPosition(self, pos):
		if pos:
			self.pos = QgsPoint(pos)
			self.setPos(self.toCanvasCoordinates(self.pos))
			self.show()
			#self.update()
		else:
			self.hide()

	def boundingRect(self):
		return QtCore.QRectF(-1,-21, 12, 22)

	def paint(self, p, xxx, xxx2):

		QP = QtCore.QPoint
		p.setRenderHint(QtGui.QPainter.Antialiasing)
		p.drawLine(QP(0,0), QP(0,-10))
		
		if self.markerType == RoutePointMarker.Start:
			p.setBrush(QtGui.QBrush(QtGui.QColor(0,255,0)))
		else:
			p.setBrush(QtGui.QBrush(QtGui.QColor(255,0,0)))

		poly = QtGui.QPolygon(3)
		poly[0] = QP(0,-10)
		poly[1] = QP(0,-20)
		poly[2] = QP(10,-15)
		p.drawPolygon(poly)

	def updatePosition(self):
		self.setPosition(self.pos)

class PositionMarker(QgsMapCanvasItem):
	""" marker for current GPS position """
    
	def __init__(self, canvas):
		QgsMapCanvasItem.__init__(self, canvas)
		self.pos = None
		self.hasPosition = False
		self.d = 20
		self.angle = 0
		self.setZValue(100) # must be on top
		
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
			
	def paint(self, p, xxx, xxx2):
		if not self.pos:
			return
		#pnt = self.toCanvasCoordinates(self.pos)
		#painter.drawRect(QtCore.QRectF(pnt.x()-self.d, pnt.y()-self.d, 2*self.d, 2*self.d))
		
		path = QtGui.QPainterPath()
		path.moveTo(0,-10)
		path.lineTo(10,10)
		path.lineTo(0,5)
		path.lineTo(-10,10)
		path.lineTo(0,-10)

		# render position with angle
		p.save()
		p.setRenderHint(QtGui.QPainter.Antialiasing)
		
		if self.hasPosition:
			p.setBrush(QtGui.QBrush(QtGui.QColor(0,0,0)))
			p.setPen(QtGui.QColor(255,255,0))
		else:
			p.setBrush(QtGui.QBrush(QtGui.QColor(200,200,200)))
			p.setPen(QtGui.QColor(255,0,0))
		
		p.rotate(self.angle)
		p.drawPath(path)
		
		if not self.hasPosition:
			f=p.font()
			f.setBold(True)
			f.setPixelSize(30)
			p.setFont(f)
			p.drawText(QtCore.QPoint(0, 0), "?")
		
		p.restore()
		
	def boundingRect(self):
		return QtCore.QRectF(-self.d,-self.d, self.d*2, self.d*2)
