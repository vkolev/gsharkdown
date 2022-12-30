from enviroment import env, config
import os
import sys
import random
from tfuncs import PlayThread
from tfuncs import SearchThread
from tfuncs import KeyListenerThread
from tfuncs import LyricsThread
from tfuncs import UpdateThread
from tfuncs import GroovesharkInitThread
from SearchResultList import SearchResultList
from PlayList import PlayList
from DownloadList import DownloadList
from Song import Song
from Song import SongCoverThread
from PlayListStyleWidget import PlayListStyleWidget
import covercache
import guihelpers
import pickle
import gtk
import gst
import glib
import gobject
import locale
import gettext
import groove
from gettext import gettext as _
from gettext import ngettext as ngettext

try:
    import pynotify
except:
    pass

try:
    import pylast
except:
    pass

class SharkDown:
    """
    The main application class for gSharkDown
    """

    def __init__(self):
        """
        Initialise the main application window
        """
        gobject.threads_init()

        self.working = None
        self.playing = None
        # just to prevend scrobbeling more then once for track.
        self.scrobbled = 0
        self.last_iter = None
        self.windowstate = 1
        self.current_song = None
        self.play_thread = None
        self.player_state_timeout_id = None
        self.is_buffering = False
        self.pynotify_object = None

        # GtkBuilder initialization
        builder = gtk.Builder()
        builder.set_translation_domain(env().APP)
        builder.add_from_file('%s/data/main_window.ui' % env().BASEPATH)

        # Main window and widgets initialization
        self.window = builder.get_object('mainwindow')
        self.window.connect("delete-event", self.window.hide_on_delete)
        self.mainmenu = builder.get_object('mainmenu')

        self.vbox_results = builder.get_object('vbox_results')
        self.hbox_filter = builder.get_object('hbox_filter')

        self.button_play = builder.get_object('button_play')
        self.button_pause = builder.get_object('button_pause')
        self.widget_image_play = builder.get_object('widget_image_play')
        self.widget_image_stop = builder.get_object('widget_image_stop')
        self.widget_image_buffering = gtk.Image()
        self.widget_image_buffering.set_from_file('%s/data/buffering.gif' % env().BASEPATH)
        self.widget_image_buffering.set_pixel_size(22)

        self.label_player_time = builder.get_object('label_player_time')
        self.label_player_trackinfo = builder.get_object('label_player_trackinfo')
        self.seekbar = builder.get_object('seekbar')
        self.button_playlist_delete = builder.get_object('button_playlist_delete')
        self.button_playlist_clear = builder.get_object('button_playlist_clear')
        self.button_save_playlist = builder.get_object('button_save_playlist')
        self.button_lyrics = builder.get_object('button_lyrics')
        self.button_lyrics.get_image().show()
        self.button_love = builder.get_object('button_love')
        self.button_songinfo = builder.get_object('button_songinfo')
        self.songinfo = builder.get_object('songinfo')

        button_repeat = builder.get_object('togglebutton_repeat')
        button_repeat.set_active(int(config()['repeat_playlist']))
        button_shuffle = builder.get_object('togglebutton_shuffle')
        button_shuffle.set_active(int(config()['shuffle_playlist']))

        combo_playlist_style = PlayListStyleWidget()
        combo_playlist_style.connect("style-changed", self.on_playlist_style_changed)
        hbox_playlist_right = builder.get_object('hbox_playlist_right')
        hbox_playlist_right.add(combo_playlist_style)

        self.panes = builder.get_object('notebook1')
        self.playview_pane_label = builder.get_object('togglebutton_playlist')
        self.playview_pane_label.get_image().show()
        self.downloads_pane_label = builder.get_object('togglebutton_downloads')

        self.entry_search = builder.get_object('toolentry_search')
        self.entry_filter = builder.get_object('entry_filter')

        # GStreamer player initialization
        self.player = gst.element_factory_make("playbin2", "player")
        self.player.connect("notify::source", self.on_player_source_setup)

        # Completition configuration
        completition = gtk.EntryCompletion()
        comp_store = gtk.ListStore(str)
        completition.set_model(comp_store)
        for item in config()['completition'].split("|"):
            comp_store.append([item])
        completition.set_minimum_key_length(1)
        completition.set_text_column(0)
        self.entry_search.set_completion(completition)

        # Results List definition
        self.result = SearchResultList(builder.get_object('list_results'))
        self.result.get_view().connect("row-activated", self.on_result_row_activated)

        # Play List definition
        self.playlist_sw = builder.get_object('playlist_sw')
        self.playlist_empty = builder.get_object('playlist_empty')
        playlist_view = builder.get_object('playlist_view')
        self.playlist = PlayList(playlist_view)
        self.playlist.get_view().connect('item-activated', self.on_playlist_double_click)
        self.playlist.get_model().connect('row-inserted', self.on_playlist_row_changed)
        self.playlist.get_model().connect('row-deleted', self.on_playlist_row_changed)

        # Download list definition
        self.downloads = DownloadList(builder.get_object('list_downloads'))
        self.downloads.connect("downloads-changed", self.on_downloads_changed)
        self.downloads.get_view().hide_all()

        # Downloads related initialization
        self.downloads_count = builder.get_object('downloads_count')
        self.downloads_expander = builder.get_object('expander_download')
        self.downmenu = builder.get_object('downloadmenu')
        self.on_downloads_changed(self.downloads, 0)

        # Song lists initialization
        if os.path.exists("%s/.gsharkdown/playlist.pkl" % os.environ.get("HOME")):
            self.load_saved_playlist("%s/.gsharkdown/playlist.pkl" % os.environ.get("HOME"))
        else:
            print "Playlist not found"

        # Downloads initialization
        if os.path.exists("%s/.gsharkdown/downqueue.pkl" % os.environ.get("HOME")):
             self.load_downqueue_list("%s/.gsharkdown/downqueue.pkl" % os.environ.get("HOME"))

        # Status icon initialization
        self.staticon = guihelpers.GsharkIndicator(self)

        # Set default directory if is empty
        if config()['down_path'] == "":
            config()['down_path'] = env().get_default_down_path()

        # Pynotify initialization
        if env().HAVE_NOTIFY:
            pynotify.init("gSharkDown")
            self.pynotify_object = pynotify.Notification("dummy", "dummy", "dummy")

        # Scrobbling initialization
        self.lastfm = None
        if env().have_pylast():
            try:
                self.lastfm = pylast.LastFMNetwork(api_key = env().LASTFM_KEY,
                                          api_secret = env().LASTFM_SECRET,
                                          username = config()['lastuser'],
                                          password_hash = config()['lastpass'])
            except pylast.WSError:
                guihelpers.ErrorMessage(self.window,
                            _("Please check your username and password for Last.fm"))

        builder.connect_signals(self)
        self.tlisten = KeyListenerThread(self)
        self.tlisten.start()

        # Updates checking
        if config()['update_checked'] == 0:
            self.check_for_updates()
        else:
            if config()['startup_update_check'] == 1:
                self.check_for_updates()

        self.window.show_all()

        self.on_playlist_row_changed(self.playlist.get_model())
        self.on_playlist_view_selection_changed(self.playlist.get_view())
        self.set_playing_song(None)
        groove.onInitStart(self.on_groove_init_start)
        groove.onInitFinish(self.on_groove_init_finish)
        groove.onInitError(self.on_groove_init_error)

    def on_groove_init_start(self):
        self.window.set_title(_("gSharkDown - Initializing Grooveshark..."))

    def on_groove_init_finish(self):
        self.window.set_title(_("gSharkDown"))

    def on_groove_init_error(self, error):
        guihelpers.ErrorMessage(self.window,
            _(
"""GrooveShark service has probably changed or is not working!
gSharkDown will not works propperly, so please be patient until we find a solution.
Also, this may usually caused by a proxy misconfiguration please check your proxy configuration.

The error was: %s""")
            % error
        )

    def on_show_playview(self, button, data = None):
        """docstring for on_show_playview"""
        if button.get_active():
            self.panes.set_current_page(0)
            self.downloads_pane_label.set_active(False)
            self.playview_pane_label.set_active(True)

    def on_show_downloadsview(self, button, data = None):
        if button.get_active():
            self.panes.set_current_page(1)
            self.playview_pane_label.set_active(False)
            self.downloads_pane_label.set_active(True)

    def on_toggle_fullscreen(self, menuitem, data = None):
        """docstring for on_toggle_fullscreen"""
        if menuitem.get_label() == "gtk-fullscreen":
            self.window.fullscreen()
            menuitem.set_label("gtk-leave-fullscreen")
        else:
            self.window.unfullscreen()
            menuitem.set_label("gtk-fullscreen")

    def on_filter_entry_icon_press(self, entry, position, event):
        entry.set_text("")

    def on_filter_changed(self, entry, data = None):
        self.result.set_filter_text(entry.get_text())

    def get_iter_last(self, model):
        """
        Get the last iter from a model
        """
        rows = model.iter_n_children(None);
        return model.get_iter([rows - 1]);

    def result_song(self, index):
        return self.result.get_song(index)

    def playlist_song(self, index):
        return self.playlist.get_song(index)

    def show_prefs_menu(self, button, data = None):
        self.mainmenu.popup(None, None, None, 0, 0)

    def load_saved_playlist(self, path):
        """
        Loads the saved playlist from .pkl file
        """
        file = open(path, 'rb')
        eoferror = True

        while eoferror:
            try:
                song = Song(pickle.load(file))
                self.playlist.append_song(song)
            except:
                eoferror = False

        file.close()

    def save_playlist(self, path):
        """
        Saves the playlist from the playlist treeview to 
        /home/$USER/.gsharkdown/playlist.pkl
        """
        try:
            output = open(path, 'w')
            for i in self.playlist.range():
                pickle.dump(self.playlist.get_song(i).get_data(), output)
            output.close()
        except:
            guihelpers.ErrorMessage(self.window, _("Error while saving the playlist"))

    def load_downqueue_list(self, path):
        """
        Loads the saved playlist from the .pkl file
        """
        file = open(path, 'rb')
        eoferror = True

        while eoferror:
            try:
                song = Song(pickle.load(file))
                self.downloads.append_song(song)
            except:
                eoferror = False

        file.close()

    def save_downqueue(self, path):
        """
        Saves the download queue to pickle file in
        /home/$USER/.gsharkdown/downqueue.pkl
        """
        try:
            output = open(path, 'w')
            for i in self.downloads.range():
                song = self.downloads.get_song(i)
                if song.get_download_progress() < 100:
                    data = self.downloads.get_song(i).get_data()
                    data["filename"] = self.downloads.get_song(i).get_filename()
                    pickle.dump(data, output, -1)
            output.close()
        except Exception, e:
            guihelpers.ErrorMessage(self.window, _("Error while saving the download queue"))


    def on_playlist_save_as(self, widget, data = None):
        """
        Saves the playlist to .pkl file in directory
        choosen from the user
        """
        savedlg = gtk.FileChooserDialog(_("Save playlist to file"),
                                       None,
                                       gtk.FILE_CHOOSER_ACTION_SAVE,
                                       (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                                       gtk.STOCK_SAVE, gtk.RESPONSE_OK))
        response = savedlg.run()

        if response == gtk.RESPONSE_OK:
            filename = savedlg.get_filename()
            if filename[-4:] != ".pkl":
                filename += ".pkl"
            self.save_playlist(filename)
        savedlg.destroy()

    def on_playlist_open(self, widget, data = None):
        """
        Opens a usersaved playlist from .pkl file
        """
        opendlg = gtk.FileChooserDialog(_("Select Playlist to open"),
                                       None,
                                       gtk.FILE_CHOOSER_ACTION_OPEN,
                                       (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                                       gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        openfilter = gtk.FileFilter()
        openfilter.set_name(_('Playlist files'))
        openfilter.add_pattern("*.pkl")

        opendlg.add_filter(openfilter)

        response = opendlg.run()

        if response == gtk.RESPONSE_OK:
            self.playlist.clear()
            self.stop_play()
            self.load_saved_playlist(opendlg.get_filename())
            self.play_first_song()
        opendlg.destroy()

    def check_for_updates(self):
        """
        Checks if a new version of the application is available
        on the application website. NEVER change the VERSION file
        manually!
        """
        t = UpdateThread()
        t.start()

    def on_check_for_updates(self, widget, data = None):
        self.check_for_updates()

    def on_quit_app(self, widget, data = None):
        """
        Confirmation dialog when exiting the application
        """
        if config()['quit_without_confirmation'] == '0':
            dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL,
                                  type = gtk.MESSAGE_QUESTION,
                                  buttons = gtk.BUTTONS_YES_NO,
                                  message_format = _("Are you sure you want to quit gSharkDown?"))
            dialog.set_title(_("Quit?"))
            response = dialog.run()
            dialog.destroy()
        else:
            response = gtk.RESPONSE_YES

        if response == gtk.RESPONSE_YES:
            covercache.analyze_cache_limit()
            self.save_playlist("%s/.gsharkdown/playlist.pkl" % os.environ.get("HOME"))
            self.save_downqueue("%s/.gsharkdown/downqueue.pkl" % os.environ.get("HOME"))
            self.downloads.stop_all_downloads()
            SongCoverThread.cancel_downloads.set()
            gtk.main_quit()

    def on_copy_song(self, widget, data = None):
        """
        Copy the selected song name from the results list in the
        GNOME Clipboard
        """
        select = self.result.get_selected_rows()
        if len(select) > 0:
            song = self.result.get_song(select[0])
            copystring = "%s - %s" % (song.get_artist(), song.get_title())
            clipboard = gtk.clipboard_get()
            clipboard.set_text(copystring)
            clipboard.store()

    def on_playlist_row_changed(self, widget, path = None, iter = None):
        if len(self.playlist.get_model()) > 0:
            self.playlist_sw.show_all()
            self.playlist_empty.hide_all()
            self.button_playlist_clear.set_sensitive(True)
            self.button_save_playlist.set_sensitive(True)
        else:
            self.playlist_empty.show_all()
            self.playlist_sw.hide_all()
            self.button_playlist_clear.set_sensitive(False)
            self.button_save_playlist.set_sensitive(False)

        if self.playlist.get_style() == PlayList.NOT_SHOW:
            self.playlist.set_style(PlayList.NOT_SHOW)

        self.update_trackinfo()

    def on_playlist_view_selection_changed(self, iconview):
        if len(self.playlist.get_selected_rows()) > 0:
            self.button_playlist_delete.set_sensitive(True)
        else:
            self.button_playlist_delete.set_sensitive(False)

    def on_playlist_style_changed(self, widget, style):
        self.playlist.set_style(style)

    def on_add_to_playlist(self, widget, data = None):
        """
        Adds selected item from the results to the playlist
        """
        select = self.result.get_selected_rows()
        for item in select:
            song = self.result.get_song(item[0])
            self.playlist.append_song(song)

    def on_remove_from_playlist(self, widget, data = None):
        """
        Removes an item from the playlist and the playitems list
        """
        selection = self.playlist.get_selected_rows()
        if len(selection) > 0:
            for i in selection:
                self.playlist.get_song(i).cancel_cover_download()
                self.playlist.get_model().remove(self.playlist.get_model().get_iter(i))

            if len(self.playlist) > 0:
                select_path = selection[len(selection) - 1]
                if select_path[0] >= len(self.playlist):
                    select_path = (select_path[0] - 1,)
                self.playlist.get_view().select_path(select_path)

            if self.get_playing_iter() == None:
                self.stop_play()

    def on_clear_playlist(self, widget, data = None):
        """
        Removes all items from the playlist
        """
        self.stop_play()
        self.playlist.get_view().select_all()
        self.on_remove_from_playlist(self.button_playlist_delete)

    def on_toggle_repeat(self, widget, data = None):
        """
        Toggles the configuration option for looping trough the
        playlist
        """
        config()['repeat_playlist'] = int(widget.get_active())
        config().write()

    def on_toggle_shuffle(self, widget, data = None):
        """
        Toggle the configuration option for shuffleing the playlist
        """
        config()['shuffle_playlist'] = int(widget.get_active())
        config().write()

    def on_playlist_double_click(self, widget, path, data = None):
        """
        Starts playling on double click event on the playlist
        treeview.
        """
        self.playlist.get_view().unselect_all()
        self.set_playing_song(self.playlist.get_song(path))

    def on_result_row_activated(self, path, column, data = None):
        """
        On double click in the search treeview the item is added to 
        the playlist and starts playling.
        """
        song = self.result.get_song(column[0])
        self.playlist.append_song(song)

    def get_playing_iter(self):
        return self.playlist.get_song_iter(self.get_playing_song())

    def on_player_message(self, bus, message):
        if message.type == gst.MESSAGE_BUFFERING or message.type == gst.MESSAGE_ASYNC_DONE:
            if (message.type == gst.MESSAGE_BUFFERING and message.parse_buffering() >= 100) or message.type == gst.MESSAGE_ASYNC_DONE:
                self.is_buffering = False
                self.button_play.set_image(self.widget_image_stop)
                self.button_pause.set_sensitive(True)
            elif not self.is_buffering:
                self.button_play.set_image(self.widget_image_buffering)
                self.is_buffering = True
        elif message.type == gst.MESSAGE_EOS:
            self.play_next()

    def on_player_source_setup(self, player, pspec):
        source = self.player.get_property("source")
        proxy = env().get_proxy()

        source.set_property("user-agent", env().USER_AGENT)
        source.set_property("cookies", ["PHPSESSID=" + groove.getSession()])

        if proxy != None:
            source.set_property("proxy", "http://" + proxy["host"] + ":" + proxy["port"])
            if proxy["user"] != None:
                source.set_property("proxy-id", proxy["user"])
                source.set_property("proxy-pw", proxy["pass"])

    def on_player_idle(self):
        try:
            duration = self.player.query_duration(gst.FORMAT_TIME)[0] / gst.SECOND
            cur = self.player.query_position(gst.FORMAT_TIME)[0] / gst.SECOND
            self.seekbar.set_range(0, duration)
            self.seekbar.set_value(cur)
            self.label_player_time.set_text("%s / %s" % (Song.format_time(cur), Song.format_time(duration)))
        except Exception, e:
            pass

        return True

    def on_seekbar_change_value(self, range, scroll, value):
        return True

    def get_playing_song(self):
        return self.playlist.get_playing_song()

    def set_playing_song(self, song):
        """
        Updates some labels and icons when a song is playing
        """
        self.playlist.set_playing_song(song)
        self.seekbar.set_value(0)
        self.update_trackinfo()
        self.label_player_time.set_text("00:00 / 00:00")
        self.player.set_state(gst.STATE_NULL)
        self.button_pause.set_sensitive(False)
        self.button_pause.set_active(False)

        if song != None:
            self.is_buffering = True

            self.staticon.change_status_playing()
            self.button_play.set_image(self.widget_image_buffering)

            self.button_songinfo.set_sensitive(True)
            self.button_lyrics.set_sensitive(True)
            if env().have_pylast():
                self.button_love.set_sensitive(True)

            self.scrobbled = 0

            self.songinfo.set_markup(
                _("<b>Playing:</b> <i>{title}</i> <span fgcolor='#777777'>by {artist}</span>").format(artist = glib.markup_escape_text(song.get_artist()),
                                         title = glib.markup_escape_text(song.get_title()))
            )
            if env().have_notify():
                self.show_playing_song_notification()

            if self.player_state_timeout_id == None:
                self.player_state_timeout_id = gobject.timeout_add(500, self.on_player_idle)

            if self.play_thread != None:
                # Avoid the current song streaming
                self.play_thread.stop()
                self.play_thread.join()
            self.play_thread = PlayThread(self, song)
            self.play_thread.start()
        else:
            if self.play_thread != None:
                self.play_thread.stop()

            if self.player_state_timeout_id != None:
                gobject.source_remove(self.player_state_timeout_id)
                self.player_state_timeout_id = None

            if env().have_notify():
                self.pynotify_object.close()

            self.staticon.change_status_stopped()
            self.button_play.set_image(self.widget_image_play)
            self.songinfo.set_markup("")

            self.button_songinfo.set_sensitive(False)
            self.button_lyrics.set_sensitive(False)
            self.button_love.set_sensitive(False)

    def show_playing_song_notification(self):
        song = self.get_playing_song()
        self.pynotify_object.update(_("Now playing"),
            "%s - %s" % (glib.markup_escape_text(song.get_artist()),
                         glib.markup_escape_text(song.get_title())),
            "audio-x-generic")
        self.pynotify_object.show()

    def play_first_song(self):
        if len(self.playlist) > 0:
            self.set_playing_song(self.playlist.get_song(0))
    
    def on_pause_toggled(self, widget):
        if self.button_pause.get_active() == True:
            self.player.set_state(gst.STATE_PAUSED)
        else:
            self.player.set_state(gst.STATE_PLAYING)
    
    def on_play_selected(self, widget, data = None, row = None):
        """
        Starts the play thread
        """
        if self.get_playing_song() == None:
            self.play_first_song()
        else:
            self.stop_play()

    def on_play_next(self, widget, data = None):
        self.play_next()

    def on_play_previous(self, widget, data = None):
        self.play_previous()

    def next_shuffled_index(self):
        path = None

        if len(self.playlist) == 1:
            return 0

        if self.get_playing_song() != None:
            path = self.playlist.get_song_path(self.get_playing_song())

        while True:
            index = random.randint(0, len(self.playlist) - 1)
            if path == None or index != path[0]:
                break

        return index

    def play_next(self):
        """
        Plays the next item from the playlist
        """
        if len(self.playlist) == 0:
            return

        if self.get_playing_song() == None:
            self.play_first_song()
        else:
            if int(config()['shuffle_playlist']) == 1:
                index = self.next_shuffled_index()
            else:
                index = self.playlist.get_song_path(self.get_playing_song())[0] + 1

            if index >= len(self.playlist):
                if int(config()['repeat_playlist']) == 1:
                    index = 0
                else:
                    index = None
                    self.stop_play()

            if index != None:
                self.set_playing_song(self.playlist.get_song((index,)))

    def play_previous(self):
        """
        Plays the previous song from the playlist
        """
        if len(self.playlist) == 0:
            return

        if self.get_playing_iter() == None:
            self.play_first_song()
        else:
            if int(config()['shuffle_playlist']) == 1:
                index = self.next_shuffled_index()
            else:
                index = self.playlist.get_song_path(self.get_playing_song())[0] - 1

            if index < 0:
                if int(config()['repeat_playlist']) == 1:
                    index = len(self.playlist) - 1
                else:
                    index = 0

            self.set_playing_song(self.playlist.get_song((index,)))

    def stop_play(self):
        """
        Stop current playing
        """
        self.set_playing_song(None)

    def update_trackinfo(self):
        if self.get_playing_song() == None:
            trackinfo_text = ngettext("%d track", "%d tracks", len(self.playlist)) % len(self.playlist)
        else:
            trackinfo_text = _("Track {0} of {1}").format(self.playlist.get_song_path(self.get_playing_song())[0] + 1,
                                                          len(self.playlist))

        self.label_player_trackinfo.set_text(trackinfo_text)

    def on_volume_change(self, widget, data = 0.5):
        """
        Volume change handler
        """
        self.player.set_property("volume", float(data))
        return True

    def on_show_info(self, widget, data = None):
        """
        Song infromation dialog for current playing song
        """
        if self.get_playing_song() != None:
            dialog = guihelpers.SongInfoDialog(self.get_playing_song())
            dialog.show_all()


    def on_show_lyrics(self, widget, data = None):
        """
        Tries to retrieve lyrics for selected song from the playlist.
        """
        if self.get_playing_song() != None:
            t = LyricsThread(self, self.get_playing_song())
            t.start()
        else:
            info = guihelpers.InfoDialog(self.window,
                _("There should be a playing song to view\nthe lyrics for it."))
            info.show_all()

    def on_show_about(self, widget, data = None):
        """
        About dialog for the application
        """
        guihelpers.AboutDialog(self)

    def on_open_preferences(self, widget, data = None):
        """
        Preferences dialog with save and close buttons
        """
        dialog = guihelpers.PreferencesDialog(self)
        dialog.show_all()

    def set_search_sensitivity(self, sens):
        self.vbox_results.set_sensitive(sens)
        self.hbox_filter.set_sensitive(sens)
        self.result.get_view().set_headers_visible(sens)
        self.result.get_view().get_column(1).set_visible(sens)
        self.result.get_view().get_column(2).set_visible(sens)

    def on_search_grooveshark(self, widget, data = None):
        """
        Starts the search thread
        """
        text = " ".join(widget.get_text().split())
        if text != "":
            if text in config()['completition'].split("|"):
                pass
            else:
                compl = config()['completition'] + text + "|"
                config()['completition'] = compl
                config().write()
            self.entry_filter.set_text("")
            search_thread = SearchThread(self, widget.get_text(), "Songs")
            search_thread.start()
            self.on_show_playview(self.downloads_pane_label)

    def on_search_text_changed(self, widget, data = None):
        t = GroovesharkInitThread()
        t.start()

    def query_download_exists(self, filename):
        # Check on downloaded files
        if os.path.exists(filename) == True:
            return True

        # Check on the downloads list
        for i in self.downloads.range():
            if filename == self.downloads.get_song(i).get_filename():
                return True

        return False

    def get_overwritten_filename(self, filename, use_response = None):
        """
        Gets the file name depending on whether user want to overwrite the file,
        not overwrite it or not save it. Returns the same filename if user want
        to overwrite, the renamed filename or None if the user cancel Download.
        """
        if self.query_download_exists(filename) == True:
            if use_response == None:
                builder = gtk.Builder()
                builder.set_translation_domain(env().APP)
                builder.add_from_file('%s/data/overwrite_dialog.ui' % env().BASEPATH)

                dialog = builder.get_object("dialog")
                label = builder.get_object("label")
                checkbox = builder.get_object("checkbutton")

                label.set_text(label.get_text() % filename)

                response = dialog.run()

                checkbox_active = checkbox.get_active()
                dialog.destroy()
            else:
                response = use_response
                checkbox_active = True
        else:
            response = 1
            checkbox_active = False

        if checkbox_active == True:
            next_response = response
        else:
            next_response = None

        if response == 2:
            i = 1
            newfilename = ""
            while i == 1 or os.path.exists(newfilename):
                i += 1
                split = os.path.splitext(filename)
                newfilename = split[0] + " (%d)" % i + split[1]

            return (newfilename, next_response)
        elif response == 1:
            return (filename, next_response)
        else:
            return (None, next_response)

    def on_download_selected(self, widget, data = None):
        """
        Starts the download thread
        """
        next_response = None
        select = self.result.get_selected_rows()
        for path in select:
            song = self.result.get_song(path)

            if self.downloads.find_song(song) == None:
                dialog_response = self.get_overwritten_filename(song.get_default_filename(), next_response)

                filename = dialog_response[0]
                next_response = dialog_response[1]

                if filename != None:
                    song.set_filename(filename)
                    self.downloads.append_song_restarting(song)

    def on_downloads_changed(self, widget, count):
        """
        Update the label wich indicates the downloads count.
        """
        text = ngettext("Downloading %d file", "Downloading %d files", count) % count
        self.downloads_count.set_label(text)

    def right_click_download(self, treeview, event):
        """
        Executed when the user rightclicks on selected items in the download list.
        Can handle single and multiple selection.
        """
        if event.button == 3:
            path = treeview.get_path_at_pos(int(event.x), int(event.y))

            if path != None:
                selection = treeview.get_selection()
                selected_rows = self.downloads.get_selected_rows()

                if not (path[0] in selected_rows):
                    selection.unselect_all()
                    selection.select_path(path[0])

                selected_rows = self.downloads.get_selected_rows()
                self.downmenu.get_children()[0].set_sensitive(False)
                self.downmenu.get_children()[1].set_sensitive(False)
                for path in selected_rows:
                    if self.downloads.get_song(path).is_downloading() == False and self.downloads.get_song(path).get_state() != Song.STATE_NOT_STARTED:
                        self.downmenu.get_children()[1].set_sensitive(True)
                    else:
                        self.downmenu.get_children()[0].set_sensitive(True)

                self.downmenu.popup(None, None, None, event.button, event.time)

                return True

    def on_cancel_all_downloads(self, widget, data = None):
        """
        Cancel all downloads
        """
        iter = self.downloads.first()
        while iter != None:
            cur = iter
            iter = self.downloads.next(iter)
            self.downloads.get_song(cur).cancel_download()

    def on_stop_all_downloads(self, widget, data = None):
        """
        Cancel all downloads
        """
        iter = self.downloads.first()
        while iter != None:
            self.downloads.get_song(iter).pause_download()
            iter = self.downloads.next(iter)

    def on_resume_all_downloads(self, widget, data = None):
        """
        Cancel all downloads
        """
        iter = self.downloads.first()
        while iter != None:
            self.downloads.get_song(iter).reset_unfinished_download_state()
            iter = self.downloads.next(iter)

    def on_clear_downloadlist(self, widget, data = None):
        """
        Clears the completed downloads from the list
        """
        iter = self.downloads.first()
        while iter != None:
            cur = iter
            iter = self.downloads.next(iter)
            song = self.downloads.get_song(cur)
            if song.get_state() == Song.STATE_COMPLETED:
                song.cancel_download()

    def on_cancel_download(self, menu, data = None):
        """
        Cancel the download. Have to check how to cancel the thread.
        """
        select = self.downloads.get_selected_rows()
        for path in select:
            song = self.downloads.get_song(path).cancel_download()

    def on_pause_download(self, button, data = None):
        """
        TODO: Not yet implemented, have to see how the download
        list will be saved.
        Stop download, in order to be resumed later
        """
        select = self.downloads.get_selected_rows()
        for path in select:
            self.downloads.get_song(path).pause_download()

    def on_resume_download(self, button, data = None):
        """
        TODO: Not yet implemnted, after stopping download we have to
        load the download list in order to resume.
        Resume stopped download
        """
        select = self.downloads.get_selected_rows()
        for path in select:
            self.downloads.get_song(path).reset_unfinished_download_state()

    def on_love_song(self, button):
        if self.get_playing_song() == None:
            info = guihelpers.InfoDialog(self.window,
                    _("There is no song to be loved.\n A song should be playing"))
            info.show_all()
        else:
            try:
                track = self.lastfm.get_track(self.get_playing_song().get_artist(),
                                          self.get_playing_song().get_title())
                track.love()
            except pylast.MalformedResponseError, e:
                pass
