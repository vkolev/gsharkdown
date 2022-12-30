from enviroment import config
from AbstractSongList import AbstractSongList
from Song import Song
import threading
import gobject
import gtk
import os
import traceback

class DownloadList(AbstractSongList):
    """
    Represent the download list
    """

    def __init__(self, view):
        self.__gobject_init__()
        AbstractSongList.__init__(self, view)
        self.downloads_count = 0

        gobject.timeout_add(300, self.on_timeout)

    def create_model(self):
        # Song, File Name, Speed, Progress, Size, Icon info stock
        return gtk.ListStore(object, str, str, int, str, str)

    def __append_song_to_model(self, song):
        song = song.clone()

        if self.find_song(song) != None:
            raise Exception()

        self.get_model().append([
            song,
            unicode(os.path.basename(song.get_filename()), errors = 'replace'),
            "",
            0,
            "",
            "gtk-network"
        ])

    def append_song(self, song):
        """
        Append song for download, if file exists, tries to continue the download
        """
        try:
            self.__append_song_to_model(song);
        except Exception:
            pass

    def append_song_restarting(self, song):
        """
        Append song for download, forcing to redownload the file
        """
        try:
            if os.path.exists(song.get_filename()):
                os.remove(song.get_filename())
            self.__append_song_to_model(song);
        except Exception:
            pass

    def create_view(self):
        self.get_view().get_selection().set_mode(gtk.SELECTION_MULTIPLE)

        column = gtk.TreeViewColumn("", gtk.CellRendererPixbuf(), stock_id = 5)
        column.set_resizable(False)
        self.get_view().append_column(column)

        column = gtk.TreeViewColumn(_("File name"), gtk.CellRendererText(), text = 1)
        column.set_resizable(True)
        self.get_view().append_column(column)

        column = gtk.TreeViewColumn(_("Speed"), gtk.CellRendererText(), text = 2)
        column.set_resizable(True)
        self.get_view().append_column(column)

        column = gtk.TreeViewColumn(_("Size"), gtk.CellRendererText(), text = 4)
        column.set_resizable(True)
        self.get_view().append_column(column)

        column = gtk.TreeViewColumn(_("Download progress"), gtk.CellRendererProgress(), value = 3)
        column.set_resizable(True)
        self.get_view().append_column(column)

    def on_timeout(self):
        downcount = 0
        next_download_path = None
        need_download = True

        for i in reversed(self.range()):
            row = self.get_model()[i]
            song = self.get_song(i)
            if song.get_state() == Song.STATE_NOT_STARTED:
                row[2] = ""
                row[5] = ""
                next_download_path = i
                downcount += 1
            elif song.get_state() == Song.STATE_CONNECTING:
                row[2] = ""
                row[5] = "gtk-network"
                need_download = False
                downcount += 1
            elif song.get_state() == Song.STATE_DOWNLOADING:
                if song.get_download_speed() == None:
                    row[2] = "N/A"
                else:
                    row[2] = "%d kB/s" % (song.get_download_speed() / 1024)
                row[3] = song.get_download_progress()
                row[4] = "%.02f MB" % (song.get_file_size() / (1024 ** 2))
                row[5] = "gtk-go-down"
                need_download = False
                downcount += 1
            elif song.get_state() == Song.STATE_COMPLETED:
                row[2] = ""
                row[3] = 100
                row[5] = "gtk-ok"
            elif song.get_state() == Song.STATE_PAUSED:
                row[2] = ""
                row[5] = "gtk-media-pause"
            elif song.get_state() == Song.STATE_CANCELED:
                self.get_model().remove(self.get_model().get_iter((i,)))
            elif song.get_state() == Song.STATE_ERROR:
                row[2] = ""
                row[5] = "gtk-dialog-error"

        if downcount != self.downloads_count:
            self.downloads_count = downcount
            self.emit("downloads-changed", downcount)

        if need_download == True and next_download_path != None:
            self.get_song(next_download_path).resume_download()

        return True

    def stop_all_downloads(self):
        """
        Stop all downloads in a sync way for quit the main app
        """
        for i in self.range():
            self.get_song(i).pause_download_sync()

gobject.type_register(DownloadList)
gobject.signal_new("downloads-changed", DownloadList, gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_INT,))
