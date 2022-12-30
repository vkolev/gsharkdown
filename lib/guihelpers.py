from enviroment import env, app, config
import gtk
import os
import sys
import locale
import gettext
import glib
from gettext import gettext as _
import webbrowser

try:
    import appindicator
except:
    pass

try:
    import pynotify
except:
    pass

try:
    import pylast
except:
    pass


class ErrorMessage(gtk.MessageDialog):
    """
    Error Message helper. Displays an Error message whit given
    text content. Used to be shown in Threads
    """

    def __init__(self, parent, message, title = _("Error")):
        """
        ErrorMessage accepts the the following parameter
        @param parent : The parent window of the error message
        @param message : The error message to be shown
        """
        gtk.MessageDialog.__init__(self, parent,
                            gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                            gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, message)
        self.set_default_response(gtk.RESPONSE_OK)
        self.set_title(title)
        self.connect('response', self.handle_clicked)

        self.show_all()

    def handle_clicked(self, *args):
        """
        Handler for the dedault dialog response.
        """
        self.destroy()

class InfoDialog(gtk.MessageDialog):
    """
    Informations dialog helper. Displays Information messages
    with given text.
    """

    def __init__(self, parent, message):
        """
        InfoDialog accepts the following parameters
        @param parent : The parent window of the Infor dialog
        @param message : The message to be shown
        """
        gtk.MessageDialog.__init__(self, parent,
                            gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                            gtk.MESSAGE_INFO, gtk.BUTTONS_OK, message)
        self.set_default_response(gtk.RESPONSE_OK)
        self.connect('response', self.handle_clicked)

    def handle_clicked(self, *args):
        """
        Handler of the default dialog response
        """
        self.destroy()

class UpdateDialog(gtk.MessageDialog):
    """
    Update dialog helper. Displays information when new version of
    gSharkDown is available.
    """
    def __init__(self, title, message, secondary):
        """
        Accepted parameters:
        @param title : The title of the update box
        @param message : The message of the update dialog
        @param secondary : The secondary message of the update dialog
        """
        gtk.MessageDialog.__init__(self, app().window,
                                   gtk.DIALOG_DESTROY_WITH_PARENT,
                                   gtk.MESSAGE_INFO, gtk.BUTTONS_OK)
        self.set_title(title)
        self.set_markup(message)
        self.format_secondary_markup(secondary)
        self.set_default_response(gtk.RESPONSE_OK)
        self.connect('response', self.handle_clicked)

    def handle_clicked(self, *args):
        """
        Handler to quit the update dialog
        """
        self.destroy()


class LyricsDialog:
    """
    Lyrics Dialog to be shown in a Thread.
    """

    def __init__(self, song, lyrics):
        """
        Accepted parameters in the Lyrics dialog
        @param song : The song
        @param lyrics : The lyrics as string to be shown in the dialog
        """
        self.builder = gtk.Builder()
        self.builder.add_from_file("%s/data/lyrics_dialog.ui" % env().BASEPATH)
        self.lyrics = self.builder.get_object('dialog1')
        self.songlabel = self.builder.get_object('label2')
        self.lyrics_view = self.builder.get_object('textview1')
        self.lyrics_buffer = self.lyrics_view.get_buffer()
        self.lyrics.add_buttons(gtk.STOCK_OK, gtk.RESPONSE_OK)
        self.lyrics.set_default_response(gtk.RESPONSE_OK)
        self.lyrics.connect('response', self.handle_clicked)
        song_title = song.get_artist() + " - "
        song_title += song.get_title()

        self.songlabel.set_text(song_title)
        self.lyrics_buffer.set_text(lyrics)

    def show_all(self):
        """
        Wrap the default function of show_all for a dialog
        """
        self.lyrics.show_all()

    def handle_clicked(self, *args):
        """
        Handler for the default dialog response
        """
        self.lyrics.destroy()

class SongInfoDialog:
    """
    Dialog that shows detailed song information
    """

    def __init__(self, song):
        self.dialog = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT,
                                      0, gtk.BUTTONS_OK,)
        self.dialog.set_title(_("Song Information - {songid}").format(songid = song.get_id()))
        _title = _("<b>Title:</b> {title}\n").format(title = glib.markup_escape_text(song.get_title()))
        _artist = _("<b>Artist:</b> {artist}\n").format(artist = glib.markup_escape_text(song.get_artist()))
        _duration = "%.2f" % (float(song.get_duration()) / 60)
        _duration = _("<b>Duration:</b> {duration} min\n").format(duration = song.get_duration_human_readable())
        _album = _("<b>Album:</b> {album}\n").format(album = glib.markup_escape_text(song.get_album()))
        _year = _("<b>Year:</b> {year}\n").format(year = song.get_year())
        info = _title + _artist + _duration + _album + _year
        self.dialog.set_markup(info)

        if song.get_cover_pixbuf() == None:
            self.set_pixbuf(gtk.gdk.pixbuf_new_from_file("%s/data/loading.png" % env().BASEPATH))
            song.connect("cover-downloaded", self.on_cover_downloaded)
            song.download_cover()
        else:
            self.set_pixbuf(song.get_cover_pixbuf())

    def show_all(self):
        self.dialog.show_all()
        self.dialog.run()
        self.dialog.destroy()

    def set_pixbuf(self, pixbuf):
        image = gtk.Image()
        image.set_from_pixbuf(pixbuf)
        self.dialog.set_image(image)
        self.dialog.show_all()

    def on_cover_downloaded(self, song):
        self.set_pixbuf(song.get_cover_pixbuf())

class PreferencesDialog:
    """
    Show a dialog for configure the preferences
    """

    def __init__(self, app):
        self.app = app

        builder = gtk.Builder()
        builder.set_translation_domain(env().APP)
        builder.add_from_file('%s/data/preferenes_dialog.ui' % env().BASEPATH)

        self.prefs = builder.get_object('window1')
        self.dest = builder.get_object('filechooserbutton1')
        self.dest.set_filename(config()['down_path'])
        self.quit_without_confirmation = builder.get_object("checkbutton1")
        self.quit_without_confirmation.set_active(int(config()['quit_without_confirmation']))
        self.bubble = builder.get_object("checkbutton2")
        self.speed = builder.get_object("spinbutton1")
        self.speed.set_value(int(config()['speed_limit']))
        self.file_pattern = builder.get_object("entry1")
        self.file_pattern.set_text(config()['file_pattern'])
        self.startup_check = builder.get_object("checkbutton4")
        self.startup_check.set_active(int(config()['startup_update_check']))
        self.edit_cover_cache_limit = builder.get_object("edit_cover_cache_limit")
        self.edit_cover_cache_limit.set_value(float(config()['cover_cache_limit']) / 1024 / 1024)

        if env().HAVE_NOTIFY:
            self.bubble.set_active(int(config()['show_notification']))
        else:
            self.bubble.set_sensitive(False)

        self.form_lastfm = builder.get_object("table_lastfm")
        self.lastuser = builder.get_object("entry_lastuser")
        self.lastuser.set_text(config()['lastuser'])
        self.lastpass = builder.get_object("entry_lastpass")
        self.lastpass.set_visibility(False)
        self.lastpass.set_text(config()['lastpass'])
        self.scrobble = builder.get_object("checkbutton_lastfm")

        if env().HAVE_PYLAST:
            self.scrobble.set_active(int(config()['scrobbling']))
            builder.get_object("label_pylasterror").destroy()
        else:
            self.scrobble.set_active(False)
            self.scrobble.set_sensitive(False)

        self.form_lastfm.set_sensitive(self.scrobble.get_active())
        builder.connect_signals(self)


        self.group_custom_proxy = builder.get_object("group_custom_proxy")
        self.radio_proxy_0 = builder.get_object("radio_proxy_0")
        self.radio_proxy_1 = builder.get_object("radio_proxy_1")
        self.radio_proxy_auto = builder.get_object("radio_proxy_auto")
        self.entry_proxy_host = builder.get_object("entry_proxy_host")
        self.entry_proxy_port = builder.get_object("entry_proxy_port")
        self.entry_proxy_user = builder.get_object("entry_proxy_user")
        self.entry_proxy_pass = builder.get_object("entry_proxy_pass")

        if config()["proxy_enabled"] == "0":
            self.radio_proxy_0.set_active(True)
        elif config()["proxy_enabled"] == "1":
            self.radio_proxy_1.set_active(True)
        else:
            self.radio_proxy_auto.set_active(True)

        self.entry_proxy_host.set_text(config()["proxy_host"])
        self.entry_proxy_port.set_text(config()["proxy_port"])
        if config()["proxy_port"] == "":
            self.entry_proxy_port.set_text("8080")
        self.entry_proxy_user.set_text(config()["proxy_user"])
        self.entry_proxy_pass.set_text(config()["proxy_pass"])

        label_proxy_info = builder.get_object("label_proxy_info")
        system_proxy = env().get_system_proxy()
        if system_proxy == None:
            label_proxy_info.set_label(_("There is no proxy configured in your system"))
        else:
            proxy_string = ""
            if system_proxy["user"] != None:
                proxy_string += system_proxy["user"] + "@"
            proxy_string += system_proxy["host"] + ":" + system_proxy["port"]
            label_proxy_info.set_label(_("The system proxy is: %s") % proxy_string)

    def show_all(self):
        self.prefs.show_all()

    def on_scrobble_toggle(self, widget, data = None):
        self.form_lastfm.set_sensitive(widget.get_active())

    def on_proxy_radio_changed(self, widget):
        self.group_custom_proxy.set_sensitive(self.radio_proxy_1.get_active())

    def on_save(self, widget, data = None):
        """
        Saves the information from the Preferences dialog in the
        configuration file
        """
        config()['down_path'] = self.dest.get_filename()

        if self.quit_without_confirmation.get_active():
            config()['quit_without_confirmation'] = '1'
        else:
            config()['quit_without_confirmation'] = '0'

        if self.bubble.get_active():
            config()['show_notification'] = 1
        else:
            config()['show_notification'] = 0

        if self.startup_check.get_active():
            config()['startup_update_check'] = 1
        else:
            config()['startup_update_check'] = 0

        config()['file_pattern'] = self.file_pattern.get_text()
        config()['speed_limit'] = self.speed.get_value_as_int()
        config()['cover_cache_limit'] = int(self.edit_cover_cache_limit.get_value() * 1024 * 1024)

        if self.radio_proxy_0.get_active():
            config()["proxy_enabled"] = "0"
        elif self.radio_proxy_1.get_active():
            config()["proxy_enabled"] = "1"
        else:
            config()["proxy_enabled"] = "auto"

        config()["proxy_host"] = self.entry_proxy_host.get_text()
        config()["proxy_port"] = self.entry_proxy_port.get_text()
        config()["proxy_user"] = self.entry_proxy_user.get_text()
        config()["proxy_pass"] = self.entry_proxy_pass.get_text()

        try:
            if self.scrobble.get_active():
                lastfm_pass = None
                lastfm_user = self.lastuser.get_text().strip()

                # Check username
                if lastfm_user == "":
                    raise Exception(_("The Last.fm username must not be empty."))

                # Check password
                if config()['lastpass'] == self.lastpass.get_text() and config()["lastuser"] == lastfm_user:
                    lastfm_pass = self.lastpass.get_text()
                elif self.lastpass.get_text() != "":
                    lastfm_pass = pylast.md5(self.lastpass.get_text())
                else:
                    raise Exception(_("The Last.fm password must not be empty."))

                lastfm = pylast.LastFMNetwork(api_key = env().LASTFM_KEY,
                                              api_secret = env().LASTFM_SECRET,
                                              username = lastfm_user,
                                              password_hash = lastfm_pass)
                self.app.lastfm = lastfm
                config()['scrobbling'] = 1
                config()['lastuser'] = lastfm_user
                config()['lastpass'] = lastfm_pass
            else:
                self.app.lastfm = None
                config()['scrobbling'] = 0

            config().write()
            self.prefs.destroy()
        except pylast.WSError:
            ErrorMessage(self.prefs, _("Please check your username and password for Last.fm or disable scrobbling"))
            self.lastuser.select_region(0, -1)
            self.lastuser.grab_focus()
            self.lastpass.set_text("")
        except Exception as e:
            ErrorMessage(self.prefs, e.args[0])
            self.lastuser.select_region(0, -1)
            self.lastuser.grab_focus()
            self.lastpass.set_text("")

    def on_cancel(self, widget, data = None):
        """
        Closes the Preferences dialog discarding any changes
        """
        self.prefs.destroy()

class AboutDialog:
    """
    Show the about dialog.
    """

    def __init__(self, app):
        builder = gtk.Builder()
        builder.set_translation_domain(env().APP)
        builder.add_from_file('%s/data/about_dialog.ui' % env().BASEPATH)
        donate = builder.get_object('button_donate')
        donate.connect("clicked", self.on_donate)
        about = builder.get_object('aboutdialog')
        about.set_version(env().VERSION)
        about.run()
        about.destroy()

    def on_donate(self, widget, data = None):
        """
        Opens the PayPal page for gSharkDown
        """
        webbrowser.open(env().DONATE_URL)

class GsharkIndicator:
    """
    AppIndicator/StatusIcon for gSharkDown
    """

    def __init__(self, app):
        """
        app parameter is the main windows class for gSharkDown,
        so we can access the gSharkDown methods.
        """
        self.app = app
        self.menu = gtk.Menu()
        self.program_changing_show_window = False

        self.show_window = gtk.CheckMenuItem(_("Show gSharkDown"))
        self.show_window.connect("toggled", self.on_statusicon_clicked)

        about = gtk.ImageMenuItem(gtk.STOCK_ABOUT)
        about.connect("activate", self.app.on_show_about)
        prefs = gtk.ImageMenuItem(gtk.STOCK_PREFERENCES)
        prefs.connect("activate", self.app.on_open_preferences)
        self.playbut = gtk.ImageMenuItem(gtk.STOCK_MEDIA_PLAY)
        self.playbut.connect("activate", self.app.on_play_selected)
        prebut = gtk.ImageMenuItem(gtk.STOCK_MEDIA_PREVIOUS)
        prebut.connect("activate", self.app.on_play_previous)
        ffbut = gtk.ImageMenuItem(gtk.STOCK_MEDIA_NEXT)
        ffbut.connect("activate", self.app.on_play_next)

        updimg = gtk.Image()
        updimg.set_from_icon_name('system-software-update',
                                 gtk.ICON_SIZE_MENU)
        updbut = gtk.ImageMenuItem(_("Check for update"))
        updbut.set_image(updimg)
        updbut.connect("activate", self.app.on_check_for_updates)
        quiter = gtk.ImageMenuItem(gtk.STOCK_QUIT)
        quiter.connect("activate", self.app.on_quit_app)

        self.menu.append(self.show_window)
        self.menu.append(gtk.SeparatorMenuItem())
        self.menu.append(prebut)
        self.menu.append(self.playbut)
        self.menu.append(ffbut)
        self.menu.append(gtk.SeparatorMenuItem())
        self.menu.append(prefs)
        self.menu.append(updbut)
        self.menu.append(about)
        self.menu.append(quiter)

        if env().HAVE_INDICATOR == True:
            self.ind = appindicator.Indicator("gsharkdown-client",
                                   "gsharkdown_indicator",
                                    appindicator.CATEGORY_APPLICATION_STATUS)
            self.ind.set_status(appindicator.STATUS_ACTIVE)
            self.ind.set_attention_icon("gsharkdown_indicator_playing")

            self.menu.show_all()
            self.ind.set_menu(self.menu)
        else:
            self.staticon = gtk.StatusIcon()
            self.staticon.set_from_file("%s/data/gsharkdown_16.png" % env().BASEPATH)
            self.staticon.connect("popup-menu", self.right_click_event)
            self.staticon.connect("activate", self.on_statusicon_clicked)
            self.staticon.set_tooltip(_("gSharkDown"))

        app.window.connect("hide", self.on_window_state_changed)
        app.window.connect("show", self.on_window_state_changed)

    def right_click_event(self, icon, button, time):
        '''
        Handler for the right click event on the StatIcon
        Not usable for the AppIndicator
        '''
        self.menu.show_all()
        self.menu.popup(None, None, gtk.status_icon_position_menu,
                  button, time, icon)

    def on_statusicon_clicked(self, widget):
        if self.program_changing_show_window == False:
            if self.app.window.get_visible():
                self.app.window.hide()
            else:
                self.app.window.present()

    def on_window_state_changed(self, widget):
        self.program_changing_show_window = True
        self.show_window.set_active(self.app.window.get_visible())
        self.program_changing_show_window = False

    def change_status_playing(self):
        # Method to change the gSharkDown icon when playing
        if env().HAVE_INDICATOR == True:
            self.ind.set_status(appindicator.STATUS_ATTENTION)
        else:
            self.staticon.set_from_file("%s/data/gsharkdown_16_playing.png" % env().BASEPATH)

        self.__change_playbutton_content(gtk.STOCK_MEDIA_STOP, _("Stop"))

    def change_status_stopped(self):
        # Method to change the gSharkDown icon to default
        # when not playing anything.
        if env().HAVE_INDICATOR == True:
            self.ind.set_status(appindicator.STATUS_ACTIVE)
        else:
            self.staticon.set_from_file("%s/data/gsharkdown_16.png" % env().BASEPATH)

        self.__change_playbutton_content(gtk.STOCK_MEDIA_PLAY, _("Play"))

    def __change_playbutton_content(self, icon_id, label):
        image = gtk.Image()
        image.set_from_stock(icon_id, gtk.ICON_SIZE_MENU)
        self.playbut.set_image(image)
        self.playbut.set_label(label)

