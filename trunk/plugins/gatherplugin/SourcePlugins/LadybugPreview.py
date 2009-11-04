# -*- coding: utf-8 -*-

from PyQt4.QtCore import *
from PyQt4.QtGui import *

class LadybugPreview(QWidget):

  def __init__(self, parent = None):
    QWidget.__init__(self, parent)
    self.pix = None
    
  def paintEvent(self, e):
    p = QPainter(self)
    
    p.drawLine(0,0,100,100)
    p.drawLine(0,100,100,0)
    
    if self.pix is not None:
      p.drawPixmap(0,0,self.pix)

  def setImg(self, i):
    self.pix = QPixmap.fromImage(i).scaled(self.size(), Qt.KeepAspectRatio)
    self.update()
    