#!/usr/bin/env python
#-*- encoding: utf-8 -*-

"""
Desktop application for downloading and playing songs provided
by the grooveshark.com service
"""

import os
import sys

# Imports with dependency check
# Imports PyGtk
try:
    import pygtk
    pygtk.require('2.0')
    import glib
    import gtk
    import gobject
except ImportError:
    print "You don't have python-gtk2 installed!"
    sys.exit(1)

# Imports GStreamer
try:
    import pygst
    pygst.require('0.10')
    import gst
except ImportError:
    print "You don't have python-gstreamer installed!"
    sys.exit(1)

# Imports ConfigObj to manage ini files
try:
    from configobj import ConfigObj
except ImportError:
    print "You don't have python-configobj installed!"
    sys.exit(1)

# Imports PyCurl
try:
    import pycurl
except:
    print "You don't have python-pycurl installed!"
    sys.exit(1)

# Imports pynotify
try:
    import pynotify
    HAVE_NOTIFY = True
except ImportError:
    print "You don't have pynotify installed!"
    HAVE_NOTIFY = False

# Imports PyLast for scrobbling with Last.fm
try:
    import pylast
    HAVE_PYLAST = True
except ImportError:
    print "You need to install pylast: sudo pip install pylast"
    HAVE_PYLAST = False

# Imports application indicator
try:
    import appindicator
    HAVE_INDICATOR = True
except ImportError:
    print "You don't have python-appindicator installed!"
    print "StautsIcon will be used instead"
    HAVE_INDICATOR = False

# Common imports
import dbus
import dbus.service
import dbus.glib
from lib.enviroment import env
from lib.SingleService import SingleService
from lib.SharkDown import SharkDown

# Enviroment Initialization
env().HAVE_NOTIFY = HAVE_NOTIFY
env().HAVE_PYLAST = HAVE_PYLAST
env().HAVE_INDICATOR = HAVE_INDICATOR
env().BASEPATH = os.path.abspath(os.path.dirname(sys.argv[0]))
env().initialize()

if __name__ == "__main__":
    owner = dbus.bus.REQUEST_NAME_REPLY_PRIMARY_OWNER
    if dbus.SessionBus().request_name("org.gsharkdown.Single") != owner:
        """
        This is just a simple salution so gsharkdown can have a 
        commandline interface, so others programs can interract with
        the application and share some informations.
        """
        try:
            if sys.argv[1] in ["--current", "-c", "current"]:
                method = dbus.SessionBus().get_object("org.gsharkdown.Single",
                            "/org/gsharkdown/Single").get_dbus_method("get_current")
            elif sys.argv[1] in ["--state", "-s", "state"]:
                method = dbus.SessionBus().get_object("org.gsharkdown.Single",
                            "/org/gsharkdown/Single").get_dbus_method("get_state")
            elif sys.argv[1] in ["--info", "-i", "info"]:
                method = dbus.SessionBus().get_object("org.gsharkdown.Single",
                            "/org/gsharkdown/Single").get_dbus_method("get_info")
            elif sys.argv[1] in ["--version", "-v", "version"]:
                method = dbus.SessionBus().get_object("org.gsharkdown.Single",
                            "/org/gsharkdown/Single").get_dbus_method("get_version")
            elif sys.argv[1] in ["--help", "-h", "help"]:
                method = dbus.SessionBus().get_object("org.gsharkdown.Single",
                            "/org/gsharkdown/Single").get_dbus_method("get_help")
            print method()
        except:
            print open("%s/HELP" % env().BASEPATH, 'r').read()
    else:
        app = SharkDown()
        env().set_app(app)
        service = SingleService(app)
        gtk.main()
