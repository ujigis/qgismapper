# -*- coding: utf-8 -*-
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
from PluginPhoto_ui import Ui_PluginPhoto
from datetime import datetime
from time import mktime
import re
import os, shutil, math
import EXIF
import Image
import ImageDraw
import ImageEnhance

filenameMatcher=re.compile("^(.*)\.([a-zA-Z0-9]*)$")
datedFilenameFormat="%Y-%m-%d_%H-%M-%S"
PhotoIconSize=30
ThumbnailBubbleDistance=QPoint(5,-10)

def filenameToUnixTime(name):
	timeStr=filenameMatcher.match(name).groups()[0]
	t=datetime.strptime(timeStr, datedFilenameFormat)
	return mktime(t.timetuple())+1e-6*t.microsecond

def unixTimeToFilename(t):
	return datetime.fromtimestamp(t).strftime(datedFilenameFormat)
	
def offsetFileName(d, d2, f, o):
	ext=filenameMatcher.match(f).groups()[1]
	newF=unixTimeToFilename(filenameToUnixTime(f)+o)+"."+ext
	os.rename(d+f, d2+newF)
	
class ImageViewer(QWidget):
	def __init__(self, parent, path, title):
		QWidget.__init__(self, parent)
		
		self.setWindowTitle(title)
		
		self.imageLabel=QLabel()
		self.imageLabel.setScaledContents(True)
		self.imageLabel.setBackgroundRole(QPalette.Base)
		scrollArea=QScrollArea()
		scrollArea.setBackgroundRole(QPalette.Dark)
		scrollArea.setWidget(self.imageLabel)
		self.layout = QVBoxLayout(self)
		self.layout.addWidget(scrollArea)
		
		self.imageLabel.setPixmap(QPixmap(path))
		self.imageLabel.resize(self.imageLabel.pixmap().size())




class ImageViewCanvasItem(QgsMapCanvasItem):
	"""Generic image viewing canvas item - not meant to be used directly."""
	
	def __init__(self, canvas, dir, iconSize):
		QgsMapCanvasItem.__init__(self, canvas)
		self.pos = None
		self.hasPosition = False
		self.iconSize=iconSize
		self.dir=dir
	
	def destroy(self):
		"""
		Method to be overloaded - called before the canvas
		item is destroyed, so that it can destroy child objects.
		"""
		pass
		
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
		width=self.iconSize+abs(ThumbnailBubbleDistance.x())
		height=self.iconSize+abs(ThumbnailBubbleDistance.y())
		return QRectF(0, -height, width, height)
		
	def isPointInside(self, pt):
		"""Returns true, if the specified point is inside item's bounding rectangle"""
		#FIXME: we need to convert pt frm layer to map coordinates here
		rect=self.boundingRect()
		rect.moveBottomLeft(self.toCanvasCoordinates(self.pos))
		return rect.contains(self.toCanvasCoordinates(pt))
	
	def overlapsWith(self, anotherItem):
		"""
		Returns true, if canvas item's bounding rectangle overlaps with
		the specified item's bounding rectangle.
		"""
		rectMy=self.boundingRect()
		rectMy.moveBottomLeft(self.toCanvasCoordinates(self.pos))
		rectHis=anotherItem.boundingRect()
		rectHis.moveBottomLeft(anotherItem.toCanvasCoordinates(anotherItem.pos))
		return rectMy.intersects(rectHis)




class PhotoCanvasItem(ImageViewCanvasItem):
	""" canvas item for showing photos over the map """

	def __init__(self, canvas, dir, fileName, pixmap, iconSize, drawPointer=True):
		ImageViewCanvasItem.__init__(self, canvas, dir, iconSize)
		self.fileName=fileName
		self.pixmap=pixmap
		self.drawPointer=drawPointer
		
		if self.pixmap.width()>self.pixmap.height():
			self.pixmapScaled=self.pixmap.scaledToWidth(self.iconSize)
		else:
			self.pixmapScaled=self.pixmap.scaledToHeight(self.iconSize)
			
	def paint(self, p, option, widget):
		if not self.pos:
			return
		
		p.setRenderHint(QPainter.Antialiasing)
		#draw a line connecting baloon with item's real world position
		if (self.drawPointer):
			p.drawLine(QPoint(0,0), ThumbnailBubbleDistance)
		
		#draw baloon border
		srcRect=QRectF(0, 0, self.pixmapScaled.width(), self.pixmapScaled.height())
		tgtRect=QRectF(0, ThumbnailBubbleDistance.y()-self.pixmapScaled.height(), self.pixmapScaled.width(), self.pixmapScaled.height())
		p.setPen(QPen(Qt.gray, 1))
		p.setBrush(QBrush(Qt.white))
		p.drawRect(tgtRect.adjusted(-2, -2, 1, 1))
		
		#draw baloon contents
		p.drawPixmap(tgtRect, self.pixmapScaled, srcRect)
	
	def onMouseButtonPressed(self, button, canvasPoint, recordingLayerPoint):
		#show image the canvas item "points to"
		self.imageView=ImageViewer(None, self.dir+self.fileName, "Photo "+self.fileName)
		self.imageView.show()



class PhotosCanvasItem(ImageViewCanvasItem):
	def __init__(self, canvas, dir, iconSize, cache):
		ImageViewCanvasItem.__init__(self, canvas, dir, iconSize)
		
		self.canvas=canvas
		self.thumbnailCache=cache
		self.thumbnailPixmaps={}
		self.thumbnailCanvasItems=None
	
	def addThumbnail(self, fileName, pixmap):
		self.thumbnailPixmaps[fileName]=pixmap
	
	def paint(self, p, option, widget):	
		if not self.pos:
			return
		
		p.setRenderHint(QPainter.Antialiasing)
		#draw a line connecting baloon with item's real world position
		p.drawLine(QPoint(0,0), ThumbnailBubbleDistance)
		
		#draw baloon border
		tgtRect=QRectF(0, ThumbnailBubbleDistance.y()-30, 30, 30)
		p.setPen(QPen(Qt.gray, 1))
		p.setBrush(QBrush(Qt.white))
		p.drawRect(tgtRect.adjusted(-2, -2, 1, 1))
		
	def onMouseButtonPressed(self, button, canvasPoint, recordingLayerPoint):
		if ImageViewCanvasItem.isPointInside(self, recordingLayerPoint):
			#click inside the item's baloon - expand/collapse contained thumbnail baloons
			if self.thumbnailCanvasItems==None:
				self.expandCanvasItem()
			else:
				self.deleteChildCanvasItems()
		else:
			#click outside item's main baloon - try contained thumbnails, whether
			#the click does match one of them (and forward the message to them)
			if self.thumbnailCanvasItems!=None:
				for ci in self.thumbnailCanvasItems:
					if ci.isPointInside(recordingLayerPoint):
						return ci.onMouseButtonPressed(button, canvasPoint, recordingLayerPoint)
	
	def destroy(self):
		self.deleteChildCanvasItems()

	def expandCanvasItem(self):
		self.thumbnailCanvasItems=[]
		size=math.ceil(math.sqrt(len(self.thumbnailPixmaps)+1))
			
		i=0
		for fileName in self.thumbnailPixmaps:
			#TODO: remove overlapping canvas items, that are already present on map?
			self.createChildCanvasItem(fileName, i, size)
			i+=1
			#skip center piece to not overlap with main canvas item
			if size%2==0:
				if ((i%size)==size/2) and (int(i/size)==size/2):
					i+=1
			else:
				if ((i%size)==math.floor(size/2)) and (int(i/size)==math.floor(size/2)):
					i+=1
				
	def createChildCanvasItem(self, fileName, index, rectSize):
		item=PhotoCanvasItem(self.canvas, self.dir, fileName, self.thumbnailPixmaps[fileName], self.iconSize, False)
		
		iconSpacing=self.iconSize*1.2
		
		posf=self.toCanvasCoordinates(self.pos)
		pos=QPoint(int(posf.x()), int(posf.y()))
		pos.setX(pos.x()+int(((index%rectSize)-rectSize/2)*iconSpacing))
		pos.setY(pos.y()+int((int(index/rectSize)-rectSize/2)*iconSpacing))
		if rectSize%2!=0:
			pos.setX(pos.x()+iconSpacing/2)
			pos.setY(pos.y()+iconSpacing/2)
			
		item.newCoords(self.toMapCoordinates(pos))
		self.thumbnailCanvasItems.append(item)
		
	def deleteChildCanvasItems(self):
		if self.thumbnailCanvasItems!=None:
			for ci in self.thumbnailCanvasItems:
				self.canvas.scene().removeItem(ci)
		self.thumbnailCanvasItems=None
		
	def isPointInside(self, pt):
		if ImageViewCanvasItem.isPointInside(self, pt):
			return True
		if self.thumbnailCanvasItems!=None:
			for ci in self.thumbnailCanvasItems:
				if ci.isPointInside(pt):
					return True
					
		return False
		
def resizeImage(fsrc, ftgt, max_width, max_height, quality, sharpness=1.6):
	"""
		Resize image fsrc (path of file), save it to ftgt; Let the maximal
		dimensions of image be (max_width,max_height), the resulting image
		quality 'quality', and do a image sharpening with 'sharpness' parameter,
		prior to saving.
	"""
	#os.system("convert '"+fsrc+"' -filter Lanczos -resize "+max_width+"x"+max_height+" -unsharp 0x0.6+1.0 -quality "+quality+" '"+ftgt+"'")
	iSrc=Image.open(fsrc)
	w=iSrc.size[0]
	h=iSrc.size[1]
	if w>=h and w>max_width:
		h=h*max_width/w
		w=max_width
	elif h>=w and h>max_height:
		w=w*max_height/h
		h=max_height
	iSrc=iSrc.resize((w, h), Image.ANTIALIAS)
	sharpener = ImageEnhance.Sharpness(iSrc)
	iSrcSharp = sharpener.enhance(sharpness)
	iSrcSharp.save(ftgt, quality=quality)
	return





class ThumbnailCreatorThread(QThread):
	"""
		Creates thumbnails of images for the ThumbnailCache class.
	"""
	def __init__(self, thumbnailCache):
		QThread.__init__(self,  QThread.currentThread())
		self.thumbnailCache=thumbnailCache
		self.mutex=QMutex()
		self.stopMe=0
		
	def run(self):
		self.mutex.lock()
		self.stopMe=0
		self.mutex.unlock()
		
		interrupted=False
		for fileName in self.thumbnailCache.photoCanvasItems:
			self.convertImage(fileName)
			
			self.mutex.lock()
			s=self.stopMe
			self.mutex.unlock()
			if s==1:
				interrupted=True
				break
		
		if not interrupted:
			self.emit(SIGNAL("cachingFinished()"))
		
	def convertImage(self, fileName):
		src=os.path.join(self.thumbnailCache.dir, fileName)
		tgt=os.path.join(self.thumbnailCache.cacheDir, fileName)
		
		if not os.path.isfile(tgt):
			resizeImage(src, tgt, 100, 100, 80, 1.2)
		self.emit(SIGNAL("thumbnailCreated(PyQt_PyObject)"), (fileName,))
		
	def stop(self):
		self.mutex.lock()
		self.stopMe=1
		self.mutex.unlock()
		
		QThread.wait(self)







class ThumbnailCache(QObject):
	"""
	Object that handles creating thumbnails of photos inside recording's direcotry
	and also required canvas items.
	"""
	def __init__(self, parent, dir, canvasItemsTimeOffset=0):
		"""
		Intitialize cache of the specified directory.
		
		@param parent parent PluginPhoto object reference
		@param dir directory, where the photos reside
		@param canvasItemsTimeOffset time offset (in seconds) that is added to photos' times
		"""
		QObject.__init__(self)
		self.parent=parent
		self.dir=dir
		self.cacheDir=dir+"thumbnails/"
		self.thumbnailCreatorThread=None
		self.photoCanvasItems={}
		self.thumbnailsPixmaps={}
		
		self.canvasItemsTimeOffset=canvasItemsTimeOffset
		
		#we need to connect the signal here, because the signal may be emited
		#before the construcor exits...
		QObject.connect(self, SIGNAL("cachingFinished()"), self.parent.cachingFinished)
		
		if not os.path.isdir(self.cacheDir):
			self.createCache()
		else:
			self.loadCache()
		
		self.lastCanvasScale=0
		QObject.connect(self.parent.controller.iface.mapCanvas(), SIGNAL("scaleChanged(double)"), self.onMapCanvasScaleChanged)
	
	def destroy(self):
		"""Prepare the object to be deleted"""
		QObject.disconnect(self.parent.controller.iface.mapCanvas(), SIGNAL("scaleChanged(double)"), self.onMapCanvasScaleChanged)
		
	def onMapCanvasScaleChanged(self, scale):
		self.recreateCanvasItems()
		
	def createCache(self):
		os.makedirs(self.cacheDir)
		self.loadCache()
	def loadCache(self):
		self.updateCache()
		
	def updateCache(self):
		"""
		Remove obsolete cachings, find uncached files and cache them.
		"""
		self.stopCaching()
		
		#remove obsolete
		for unusedFile in [f for f in os.listdir(self.cacheDir) if not os.path.isfile(os.path.join(self.dir, f))]:
			os.remove(os.path.join(self.cacheDir, unusedFile))
			if self.photoCanvasItems.has_key(unusedFile):
				self.deleteImage(unusedFile)
				del self.photoCanvasItems[unusedFile]
		
		#make list of files to be cached
		for uncachedFile in [f for f in os.listdir(self.dir) if os.path.isfile(os.path.join(self.dir, f))]:
			if not self.photoCanvasItems.has_key(uncachedFile):
				self.photoCanvasItems[uncachedFile]=None
	
		if self.photoCanvasItems!={}:
			self.startCaching()
		else:
			self.emit(SIGNAL("cachingFinished()"))
		
	def startCaching(self):
		"""Start creating thumbnails a in separate thread"""
		self.thumbnailsPixmaps={}
		self.thumbnailCreatorThread=ThumbnailCreatorThread(self)
		QObject.connect(self.thumbnailCreatorThread, SIGNAL("cachingFinished()"), self.cachingFinished)
		QObject.connect(self.thumbnailCreatorThread, SIGNAL("thumbnailCreated(PyQt_PyObject)"), self.thumbnailCreated)
		self.parent.caching_progressBar.setRange(0, len(self.photoCanvasItems))
		self.parent.caching_progressBar.setValue(0)
		self.thumbnailCreatorThread.start()
		self.timer = QTimer()
		QObject.connect(self.timer, SIGNAL("timeout()"), self.runStatusTicker)
		self.timer.start(10)
	
	def runStatusTicker(self):
		#TODO: this probably causes the qgis to dead-lock somewhere inside sip handler :-(
		#unfortunately without this, the caching is at like 1/10 of the full speed...
		
		#self.thumbnailCreatorThread.msleep(1)
		pass
		
	def cachingFinished(self):
		"""Handle end of thumbnail creating thread."""
		self.emit(SIGNAL("cachingFinished()"))
		self.timer.stop()
		del self.timer
		self.stopCaching()
		
		self.recreateCanvasItems()
		
	def thumbnailCreated(self, params):
		"""Handle new-thumbnail-created event of thumbnail creator thread."""
		#TODO: optimize using QPixmapCache
		(fileName,)=params
		self.thumbnailsPixmaps[fileName]=QPixmap(os.path.join(self.cacheDir, fileName))
		self.parent.caching_progressBar.setValue(self.parent.caching_progressBar.value()+1)
		
	def stopCaching(self):
		"""Cancel thumbnail creating"""
		if self.thumbnailCreatorThread!=None:
			self.thumbnailCreatorThread.stop()
			self.thumbnailCreatorThread=None
	
	def deleteAllImages(self):
		self.deleteAllCanvasItems()
		self.photoCanvasItems={}
	
	def deleteAllCanvasItems(self):
		for item in self.photoCanvasItems:
			self.deleteImage(item)
			
	def deleteImage(self, item):
		"""Delete the specified image's canvas item"""
		if self.photoCanvasItems[item]!=None:
			self.parent.controller.iface.mapCanvas().scene().removeItem(
				self.photoCanvasItems[item]
			)
			self.photoCanvasItems[item].destroy()
			self.photoCanvasItems[item]=None
	
	def recreateCanvasItems(self):
		"""Create canvas items containing thumbnails"""
		
		#ignore small scale changes
		if (self.lastCanvasScale!=0) and (abs(self.lastCanvasScale-self.parent.controller.iface.mapCanvas().scale())/self.lastCanvasScale<0.05):
			return
		self.lastCanvasScale=self.parent.controller.iface.mapCanvas().scale()
		
		if self.thumbnailCreatorThread!=None:
			return
		
		self.deleteAllCanvasItems()

		for fileName in self.thumbnailsPixmaps:
			item=self.createPhotoCanvasItem(fileName)
			
			overlapsWith=self.findOverlappingCanvasItem(item)
			
			if overlapsWith==None:
				self.photoCanvasItems[fileName]=item
			else:
				#delete previous image canvas item and create multi-image canvas instead
				self.parent.controller.iface.mapCanvas().scene().removeItem(item)
				
				if isinstance(self.photoCanvasItems[overlapsWith], PhotoCanvasItem):
					self.deleteImage(overlapsWith)
					self.photoCanvasItems[overlapsWith]=self.createPhotosCanvasItem(overlapsWith)
				
				self.photoCanvasItems[overlapsWith].addThumbnail(fileName, self.thumbnailsPixmaps[fileName])
				
	def createPhotoCanvasItem(self, fileName):
		"""Create canvas item for the specified photo"""
		item=PhotoCanvasItem(
			self.parent.controller.iface.mapCanvas(),
			self.dir,
			fileName,
			self.thumbnailsPixmaps[fileName],
			PhotoIconSize
		)

		item.newCoords(
			self.parent.controller.gpxFile.getTrkPtAtIndex(
				self.parent.controller.gpxFile.getTrkPtAtTime(
					filenameToUnixTime(fileName)+self.canvasItemsTimeOffset
				)
			).getQGisCoords()
		)
		return item
	
	def createPhotosCanvasItem(self, firstImage):
		"""Create canvas item for the multiple photos, with specified photo as the first one"""
		item=PhotosCanvasItem(
			self.parent.controller.iface.mapCanvas(),
			self.dir,
			PhotoIconSize,
			self
		)

		item.newCoords(
			self.parent.controller.gpxFile.getTrkPtAtIndex(
				self.parent.controller.gpxFile.getTrkPtAtTime(
					filenameToUnixTime(firstImage)+self.canvasItemsTimeOffset
				)
			).getQGisCoords()
		)
		item.addThumbnail(firstImage, self.thumbnailsPixmaps[firstImage])
		
		return item
	
	def findOverlappingCanvasItem(self, item):
		"""Find canvas item overlapping the specified one, if any"""
		overlapsWith=None
		for img in self.photoCanvasItems:
			if self.photoCanvasItems[img]==None:
				continue
				
			if self.photoCanvasItems[img].overlapsWith(item):
				overlapsWith=img
				break
		return overlapsWith
	
	def get_canvasItems(self):
		for img in self.photoCanvasItems:
			if self.photoCanvasItems[img]!=None:
				yield img
	canvasItems=property(get_canvasItems, lambda x:x)




class PluginPhoto(QWidget, Ui_PluginPhoto):	
	def __init__(self, controller, parent=None):
		QWidget.__init__(self, parent)
		self.controller=controller
		
		self.setupUi(self)
		self.name="Photo"
		
		self.thumbnailCache=None
		
		QObject.connect(self.addPictures_button, SIGNAL("clicked()"), self.addPictures)
		QObject.connect(self.timeOffset_secs_spinBox, SIGNAL("valueChanged(int)"), self.checkTimeOffsetValues)
		
		QObject.connect(self.timeOffset_preview_pushButton, SIGNAL("clicked()"), self.reloadThumbnailsCache)
		QObject.connect(self.timeOffset_save_pushButton, SIGNAL("clicked()"), self.retimePhotos)
		
		QObject.connect(self.photos_remove_button, SIGNAL("clicked()"), self.removeSelectedPhotos)

	def loadRecording(self, dataDirectory):
		self.dataDirectory=dataDirectory+self.name+"/"
		self.resetEnteredTimeOffset()
		self.reloadThumbnailsCache()
		
	def reloadThumbnailsCache(self):
		self.unloadThumbnailsCache()
		self.thumbnailCache=ThumbnailCache(self, self.dataDirectory, self.getEnteredTimeOffset())
	
	def unloadThumbnailsCache(self):
		if self.thumbnailCache!=None:
			self.thumbnailCache.stopCaching()
			self.thumbnailCache.deleteAllImages()
			self.thumbnailCache.destroy()
			self.thumbnailCache=None
		
	def cachingFinished(self):
		if self.thumbnailCache:
			files=self.thumbnailCache.photoCanvasItems.keys()
			files.sort()
		else:
			files=()
		
		self.photos_list.clear()
		for f in files:
			self.photos_list.addItem(f)
		
		photosAvailable=self.photos_list.count()!=0
		self.photos_list.setEnabled(photosAvailable)
		self.timeOffset_groupBox.setEnabled(photosAvailable)
		self.photos_remove_button.setEnabled(photosAvailable)
		
	def updateReplayToTime(self, time):
		pass
	def seekReplayToTime(self, time):
		return
	
	def unloadRecording(self):
		self.unloadThumbnailsCache()
		self.photos_list.clear()
		
	def addPictures(self):
		"""
			Add already taken pictures to recording. If no recording is ongoing,
			ask user what data directory he wants to put the photos into.
		"""
		dir=self.dataDirectory
			
		#append self.name, if requiredself.
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
		
		if files==[]:
			return
		
		errorFiles=""
		for f in files:
			fh=open(f, "rb")
			exif=EXIF.process_file(fh)
			fh.close()
			
			try:
				newfn=dir+str(exif["Image DateTime"]).replace(":", "-").replace(" ", "_")+f[f.rfind("."):]
				shutil.copy2(f, newfn)
			except:
				errorFiles=errorFiles+f+"\n"
		
		if errorFiles!="":
			QMessageBox.warning(self, self.tr("Unprocessed files"), self.tr("The following files were not added (exif info/unsupported format): \n")+errorFiles)
			
		self.reloadThumbnailsCache()
		
	def onMouseButtonPressed(self, button, canvasPoint, recordingLayerPoint):
		"""Handle mouse button pressed action by forwarding the message to correct canvas item"""
		if self.thumbnailCache==None:
			return False
			
		for f in self.thumbnailCache.canvasItems:
			if self.thumbnailCache.photoCanvasItems[f].isPointInside(recordingLayerPoint):
				self.thumbnailCache.photoCanvasItems[f].onMouseButtonPressed(button, canvasPoint, recordingLayerPoint)
				return True
		return False

	def getEnteredTimeOffset(self):
		return self.timeOffset_mins_spinBox.value()*60+self.timeOffset_secs_spinBox.value()
		
	def resetEnteredTimeOffset(self):
		self.timeOffset_mins_spinBox.setValue(0)
		self.timeOffset_secs_spinBox.setValue(0)

	def checkTimeOffsetValues(self, val):
		mins=self.timeOffset_mins_spinBox.value()
		secs=self.timeOffset_secs_spinBox.value()
		if secs==60:
			self.timeOffset_mins_spinBox.setValue(mins+1)
			self.timeOffset_secs_spinBox.setValue(0)
		elif secs==-60:
			self.timeOffset_mins_spinBox.setValue(mins-1)
			self.timeOffset_secs_spinBox.setValue(0)
		elif mins<0 and secs>0:
			self.timeOffset_mins_spinBox.setValue(mins+1)
			self.timeOffset_secs_spinBox.setValue(-(60-secs))
		elif mins>0 and secs<0:
			self.timeOffset_mins_spinBox.setValue(mins-1)
			self.timeOffset_secs_spinBox.setValue(60+secs)
	
	def retimePhotos(self):
		"""
		Update time of photos of current recording according to current time offset
		entered by the user.
		"""
		self.unloadThumbnailsCache()
		
		dirs=[self.dataDirectory, self.dataDirectory+"thumbnails/"]
		for dir in dirs:
			#first move images to a temporary directory
			tmpDir=dir+"tmp/"
			os.makedirs(tmpDir)
			
			files=[x for x in os.listdir(dir) if os.path.isfile(dir+x)]
			
			#calculate new images' times
			for f in files:
				offsetFileName(dir, tmpDir, f, self.getEnteredTimeOffset())
			
			#move the images back to original directory
			for f in os.listdir(tmpDir):
				os.rename(tmpDir+f, dir+f)
			
			#remove temporary directory
			os.rmdir(tmpDir)
		
		#reset offset and reload thumbnails
		self.resetEnteredTimeOffset()
		self.reloadThumbnailsCache()
	
	def removeSelectedPhotos(self):
		"""Delete selected photos (in list widget) from disk."""
		if QMessageBox.question(self,
			self.tr("Delete files"),
			self.tr("Do you really want to delete selected files?"),
			QMessageBox.Yes,
			QMessageBox.No
		)==QMessageBox.No:
			return
		
		for i in self.photos_list.selectedIndexes():
			os.remove(self.dataDirectory+i.data().toString())
			
		self.reloadThumbnailsCache()
		
def getInstance(controller):
	return PluginPhoto(controller)
