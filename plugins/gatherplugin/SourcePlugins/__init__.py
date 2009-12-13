# -*- coding: utf-8 -*-
import os, sys
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import re
import traceback

LOAD_DUMMYPLUGIN=False #Should the dummy plugin be loaded?

def loadPlugins(controller):
	"""
	Loads all 'data source' plugins from current directory.
	A data source plugin has to be named Plugin*.py (where * is
	a string made of alphanumeric characters). The plugin file
	is first imported and getInstance() method is called afterwards
	to retrieve the plugin object (which gatherer comunicates with later).
	"""
	global loadedPlugins
	loadedPlugins=[]

	#load all the plugins
	pluginRe=re.compile('^(Plugin[a-zA-Z0-9]*)\.py$', re.IGNORECASE)
	pluginReNot=re.compile('^(Plugin[a-zA-Z0-9]*Worker)\.py$', re.IGNORECASE)
	for file in os.listdir(__path__[0]):
		m=pluginRe.match(file)
		m2=pluginReNot.match(file)
		if m!=None and m2==None and (
			(LOAD_DUMMYPLUGIN==False and m.group(1)!="PluginDummy") or LOAD_DUMMYPLUGIN==True
		):
			try:
				exec 'import '+m.group(1)
				exec 'plugin='+m.group(1)+'.getInstance(controller)'
				if plugin!=None:
					loadedPlugins.append(plugin)
			except:
				print "Gatherer: error loading plugin "+m.group(1)
				traceback.print_exc(file=sys.stdout)

def unloadPlugins():
	"""
	Notify plugins about unloading and then free=delete them.
	"""
	global loadedPlugins
	
	for plugin in loadedPlugins:
		if "unload" in dir(plugin):
			plugin.unload()
	loadedPlugins=[]

def initializeUI(tabWidget):
	"""
	Initialize user interface of plugins. This happens by calling
	finalizeUI method of the plugin.
	"""
	for plugin in loadedPlugins:
		tabWidget.addTab(plugin, plugin.name)
		if "finalizeUI" in dir(plugin):
			plugin.finalizeUI()

def callMethodOnEach(method, *params):
	"""
	Calls the specified method (with parameters params) of all
	loaded plugin objects.
	"""
	for plugin in loadedPlugins:
		try:
			if method in dir(plugin):
				apply(getattr(plugin, method), *params)
			else:
				pass #print "method %s not implemented in %s" % (method, plugin.name)
		except:
			print "Exception @", plugin.name
			traceback.print_exc(file=sys.stdout)
