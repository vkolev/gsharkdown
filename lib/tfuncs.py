from enviroment import env, config
import os
import sys
import gtk
import dbus
import dbus.service
import dbus.mainloop.glib
import time
import threading
import groove
import lyrdblib
import guihelpers
import urllib2
import gobject
from Song import Song
import traceback

import locale
import gettext
from gettext import gettext as _

import pygst
import gst
import pycurl

class GroovesharkInitThread(threading.Thread):
    def run(self):
        if groove.isInitialized() == False:
            groove.init()

class PlayThread(threading.Thread):

    def __init__(self, app, song):
        """
        Start the player thread with the following parameters:
        @param app: The application instance
        @param song: The song to play
        """
        threading.Thread.__init__(self)
        self.app = app
        self.song = song
        self._stop = threading.Event()

    def run(self):
        # This avoid madness when user press repeatedly the prev and next button
        # The song streaming begins if the thread is not canceled in one second
        self._stop.wait(1)
        if self.stopped():
            return

        try:
            play_url = self.song.get_streaming_url()
        except Exception as e:
            traceback.print_exc(file = sys.stdout)
            gobject.idle_add(self.on_playing_error, e.__str__())
            return

        if self.stopped():
            return

        print "[Playing]", self.song.get_id(), play_url
        self.app.player.set_property('uri', play_url)
        self.app.player.set_state(gst.STATE_PLAYING)
        if self.app.lastfm != None:
            if self.app.scrobbled == 0:
                self.app.lastfm.scrobble(self.song.get_artist(),
                                    self.song.get_title(),
                                    int(time.time()))
                self.app.lastfm.update_now_playing(self.song.get_artist(),
                                              self.song.get_title())
                self.app.scrobbled = 1
            else:
                pass
        bus = self.app.player.get_bus()
        bus.enable_sync_message_emission()
        bus.add_signal_watch()
        bus.connect('message', self.app.on_player_message)

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()

    def on_playing_error(self, error):
        guihelpers.ErrorMessage(self.app.window, _("An error occurred while playing the song. Please try again later.\n\nThe error was: %s") % error)
        self.app.set_playing_song(None)


class KeyListenerThread(threading.Thread):

    def __init__(self, app):
        """
        A thread to listen for multimedia key press
        Accepts as parameter:
        @param _window : The main window, to interact with
        """
        threading.Thread.__init__(self)
        self.app = app

    def run(self):
        """
        Run as a dbus deamon
        """
        try:
            dbus.mainloop.glib.DBusGMainLoop(set_as_default = True)
            bus = dbus.Bus(dbus.Bus.TYPE_SESSION)
            bus_object = bus.get_object('org.gnome.SettingsDaemon',
                                '/org/gnome/SettingsDaemon/MediaKeys')

            dbus_interface = 'org.gnome.SettingsDaemon.MediaKeys'
            bus_object.GrabMediaPlayerKeys("MyMultimediaThingy", 0,
                                  dbus_interface = dbus_interface)

            bus_object.connect_to_signal('MediaPlayerKeyPressed',
                                self.on_media_key)
        except:
            pass

    def on_media_key(self, comes_from, what):
        """
        If a key was press see where it comes from and what key it is
        """
        if what in ['Stop', 'Play', 'Next', 'Previous']:
            if what == 'Stop':
                gobject.idle_add(self.app.on_play_selected, self.app.button_play)
            elif what == 'Play':
                gobject.idle_add(self.app.on_play_selected, self.app.button_play)
            elif what == 'Next':
                gobject.idle_add(self.app.on_play_next)
            elif what == 'Previous':
                gobject.idle_add(self.app.on_play_previous)

class SearchThread(threading.Thread):

    def __init__(self, app, query, type):
        """
        A search thread class accepts as parameters:
        @param app : The main window to interact with
        @param query : The search term that was put in
        @param type : Type of the search to be done
        """
        threading.Thread.__init__(self)
        self.app = app
        self.query = query
        self.type = type
        self.app.entry_search.set_sensitive(False)

    def run(self):
        try:
            results = groove.getSearchResultsEx(self.query, self.type)
            gobject.idle_add(self.fill_results, results)
        except Exception as e:
            gobject.idle_add(self.search_error, e.__str__())

    def fill_results(self, results):
        self.app.entry_search.set_sensitive(True)
        self.app.result.clear()
        if results and len(results) > 0:
            self.app.set_search_sensitivity(True)
            for song_data in results:
                self.app.result.append_song(Song(song_data))
        else:
            self.app.set_search_sensitivity(False)
            self.app.result.get_full_model().append([
                None,
                "<span foreground='#555555'>%s</span>" % _("No songs found"),
                "",
                ""
            ])
    def search_error(self, error):
        self.app.entry_search.set_sensitive(True)
        self.app.set_search_sensitivity(True)
        guihelpers.ErrorMessage(self.app.window, _("An error occurred while search on Grooveshark.\n\nThe error was: %s") % error)


class UpdateThread(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):

        remote = urllib2.urlopen(env().UPDATE_URL)
        self.remoteversion = remote.read().replace('\n', '')

        if self.remoteversion > env().VERSION:
            gobject.idle_add(self.show_update_dialog, True)
        else:
            gobject.idle_add(self.show_update_dialog, False)

    def show_update_dialog(self, is_update):
        config()['update_checked'] = 1
        config().write()

        secondary_text = _("To update to the latest version ")
        secondary_text += _("you can visit the <a href=\"http://https://bitbucket.org/vkolev/gsharkdown/downloads\"> ")
        secondary_text += _("download site</a>. If you are using the latest version and want to be ")
        secondary_text += _("informed about new versions, just enable the option in the <b>Preferences</b> dialog.")

        if is_update:
            main_text = _("<b>New version <span fgcolor=\"red\"><i>%s</i></span> is available</b>")

            dialog = guihelpers.UpdateDialog(_('New version'),
                                                 main_text % self.remoteversion,
                                                 secondary_text)
            dialog.show_all()
        else:
            main_text = _("<b>You are using the latest version!</b>")

            dialog = guihelpers.UpdateDialog(_('Latest version'),
                                             main_text,
                                             secondary_text)
            dialog.show_all()


class LyricsThread(threading.Thread):

    def __init__(self, app, song):
        """
        Thread for searching lyrics for a specified song with given
        artist and songname.
        """
        threading.Thread.__init__(self)
        self.app = app
        self.song = song
        self.app.button_lyrics.set_sensitive(False)
        self.app.button_lyrics.set_label(_("Loading lyrics..."))

    def run(self):
        lyrics = lyrdblib.search(self.song.get_artist(), self.song.get_title())
        gobject.idle_add(self.open_viewer, lyrics)

    def open_viewer(self, lyrics):
        self.app.button_lyrics.set_sensitive(True)
        self.app.button_lyrics.set_label(_("Lyrics"))
        if "ERROR:" in lyrics:
            guihelpers.ErrorMessage(self.app.window, lyrics)
        else:
            lyrdiag = guihelpers.LyricsDialog(self.app.get_playing_song(), lyrics)
            lyrdiag.show_all()


