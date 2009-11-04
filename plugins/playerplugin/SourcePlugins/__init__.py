# -*- coding: utf-8 -*-
import os, sys
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import re
import xml.dom.minidom
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
				loadedPlugins.append(plugin)
			except:
				print "Player: error loading plugin "+m.group(1)
				traceback.print_exc(file=sys.stdout)

def initializeUI(tabWidget):
	"""
	initialize user interface of plugins
	"""
	for plugin in loadedPlugins:
		tabWidget.addTab(plugin, plugin.name)

def loadConfig(rootElement):
	"""
	Load plugins' configurations from under specified xml element.
	This happens by calling the loadConfig method of plugin.
	"""
	configuredPlugins=[]
	
	for e in range(0, rootElement.count()):
		element=rootElement.item(e).toElement()
		
		for plugin in loadedPlugins:
			e_cnf=element.elementsByTagName(plugin.name)
			if (e_cnf.count()!=0):
				plugin.loadConfig(e_cnf.item(0).toElement())
				configuredPlugins=configuredPlugins+[plugin.name]

	for plugin in loadedPlugins:
		if not plugin.name in configuredPlugins:
			plugin.loadConfig(None)
	

def saveConfig(doc, rootElement):
	"""
	Save plugins' configurations under specified xml element.
	This happens by calling the saveConfig method of plugin.
	"""
	for plugin in loadedPlugins:
		e_cnf=doc.createElement(plugin.name)
		plugin.saveConfig(e_cnf)
		rootElement.appendChild(e_cnf)
	
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

def callMethodOnEachAndGetCumulativeReturnValue(method, *params):
	"""
	Calls the specified method (with parameters params) of all
	loaded plugin objects. Returns Or'd value of all values returned by plugins.
	"""
	rv=0
	for plugin in loadedPlugins:
		try:
			if method in dir(plugin):
				rv|=apply(getattr(plugin, method), *params)
			else:
				pass #print "method %s not implemented in %s" % (method, plugin.name)
		except:
			print "Exception @", plugin.name
			traceback.print_exc(file=sys.stdout)
	return rv
