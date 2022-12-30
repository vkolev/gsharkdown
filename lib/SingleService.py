from enviroment import env
import dbus
import dbus.service
import dbus.glib
import glib

class SingleService(dbus.service.Object):
    """
    Class to ensure that gSharkDown is running as a single service
    and allow command line arguments to be passed to the application
    """

    def __init__(self, app):
        self.app = app
        bus_name = dbus.service.BusName('org.gsharkdown.Single',
                                       bus = dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, '/org/gsharkdown/Single')

    @dbus.service.method(dbus_interface = 'org.gsharkdown.Single')
    def get_current(self):
        """
        Method to get the current playing song used in the
        commandline interface.
        """
        if self.app.get_playing_song() == None:
            return "gSharkDown is not playing"
        else:
            song = self.app.get_playing_song().get_artist()
            song = song + " - "
            song = song + self.app.get_playing_song().get_title()
            return song

    @dbus.service.method(dbus_interface = 'org.gsharkdown.Single')
    def get_state(self):
        """
        Method to get the player state used in the commandline interface
        """
        if self.app.get_playing_song() == None:
            return "Stopped"
        else:
            return "Playing"

    @dbus.service.method(dbus_interface = 'org.gsharkdown.Single')
    def get_info(self):
        """
        Method to get information about the current playing song
        artist, song, album, year. Used in the commandline interface
        """
        if self.app.get_playing_song() == None:
            return ""
        else:
            song = self.app.get_playing_song()
            info = "Artist: " + glib.markup_escape_text(song.get_artist()) + "\n"
            info += "Song:" + glib.markup_escape_text(song.get_title()) + "\n"
            info += "Album:" + glib.markup_escape_text(song.get_album()) + "\n"
            info += "Year:" + song.get_year() + "\n"
            return info

    @dbus.service.method(dbus_interface = 'org.gsharkdown.Single')
    def get_version(self):
        """
        Method to return the current version of gSharkDown.
        """
        return env().VERSION

    @dbus.service.method(dbus_interface = 'org.gsharkdown.Single')
    def get_help(self):
        """
        Method to read the HELP file and display the help message
        when using the commandline interface.
        """
        return open("%s/HELP" % env().BASEPATH, 'r').read()
