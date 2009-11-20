# -*- coding: utf-8 -*-

"""
A simple tool for creating packages of plugins and updating repository XML.

(c) 2009 Martin Dobias

Licensed under GNU GPL v2
"""

import os
import zipfile
import xml.etree.ElementTree as ET

# plugins to be packaged and included in repository
plugins = ['gatherplugin', 'playerplugin']


def make_plugin(dirname):
  """ Run make command for the plugin """
  os.chdir(dirname)
  # make sure there are no .pyc files
  if os.spawnlp(os.P_WAIT, 'make', dirname, 'clean') != 0:
    raise OSError("Make clean failed!")
  if os.spawnlp(os.P_WAIT, 'make', dirname) != 0:
    raise OSError("Make failed!")
  os.chdir('..')


def list_files(dirname):
  """ Recursively walk dirname and return list of all files """
  lst = []
  for (root,dirs,files) in os.walk(dirname):
    lst.append(root)
    lst += map(lambda x: os.path.join(root,x), files)

    # prune .svn dirs
    if '.svn' in dirs: dirs.remove('.svn')
  return lst

def create_zip_file(zipname, files):
  """ Create ZIP file called zipname that contains specified files """
  f = zipfile.ZipFile(zipname, "w", zipfile.ZIP_DEFLATED)
  for item in files:
    #print "adding", item
    f.write(item)
  f.close()


def get_plugin_metadata(pluginname):
  """ return plugin's metadata as a tuple: visible name, version, description, author """
  pluginmodule = __import__(pluginname)
  visiblename = pluginmodule.name()
  desc = pluginmodule.description()
  ver_string = pluginmodule.version()
  # version returns usually "Version 0.1" - get only the second part
  version = ver_string.split(' ')[1]
  return (visiblename, version, desc)

def create_plugin_element(pluginname, metadata):
  """ create DOM element with plugin's details """
  visiblename, version, desc = metadata
  zipname = pluginname+".zip"
  elem = ET.Element('pyqgis_plugin', name=visiblename, version=version)
  ET.SubElement(elem, "description").text = desc
  ET.SubElement(elem, "homepage").text = "http://code.google.com/p/qgismapper/"
  ET.SubElement(elem, "qgis_minimum_version").text = "1.0.0"
  ET.SubElement(elem, "file_name").text = zipname
  ET.SubElement(elem, "author_name").text = "Andrej Krutak, Martin Dobias"
  ET.SubElement(elem, "download_url").text = "http://qgismapper.googlecode.com/svn/trunk/plugins/"+ zipname
  return elem


### RUN!

root = ET.Element("plugins")

for pluginname in plugins:
  make_plugin(pluginname)
  create_zip_file(pluginname+'.zip', list_files(pluginname))
  print "%s: created ZIP file" % pluginname
  metadata = get_plugin_metadata(pluginname)
  print "%s: metadata %s" % (pluginname, str(metadata))
  root.append(create_plugin_element(pluginname, metadata))

ET.ElementTree(root).write("plugins.xml")

print "DONE"
