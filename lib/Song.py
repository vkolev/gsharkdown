from enviroment import env, config
import os
import gtk
import gobject
import threading
import pycurl
import time
import groove
import math
import covercache

class Song(gobject.GObject):
    """
    This class encasuplates a handle song information.
    """

    """
    Song data example:
    {
        u'SongID': 8428135, 
        u'IsLowBitrateAvailable': 1, 
        u'AvgDuration': 199, 
        u'Year': '', 
        u'Popularity': 1128700160, 
        u'SongName': u'Me gustas mucho', 
        u'AlbumName': u'Especial', 
        u'TrackNum': 3, 
        u'AlbumID': 1318743, 
        u'ArtistID': 12057, 
        u'Score': 156174.67887245, 
        u'Flags': 0, 
        u'EstimateDuration': 198, 
        u'AvgRating': 0, 
        u'CoverArtFilename': u'1318743.jpg', 
        u'TSAdded': u'1210029617', 
        u'GenreID': 7, 
        u'IsVerified': 1, 
        u'ArtistName': u'Viejas Locas'
    }
    """
    STATE_NOT_STARTED = 0
    STATE_CONNECTING = 1
    STATE_DOWNLOADING = 2
    STATE_COMPLETED = 3
    STATE_PAUSED = 4
    STATE_CANCELED = 5
    STATE_ERROR = 6
    last_song_local_id = 0

    def __init__(self, data):
        """
        @param data: The array data given by GrooveShark. This array also can has a
        key called 'filename', it is used to initialize the Song with a filename,
        used mainly by the app when load the downqueue file to know on wich file should
        download the song.
        """
        self.__gobject_init__()
        Song.last_song_local_id += 1

        self.local_id = Song.last_song_local_id
        self.data = data
        self.cover_pixbuf = None
        self.filename = None
        self.state = Song.STATE_NOT_STARTED
        self.download_thread = None
        self.cover_thread = None
        self.last_error = None

        try:
            self.filename = self.data["filename"]
        except KeyError:
            self.filename = self.get_default_filename()

        self.connect("download-initializing", self.on_download_initializing)
        self.connect("download-started", self.on_download_started)
        self.connect("download-paused", self.on_download_paused)
        self.connect("download-canceled", self.on_download_canceled)
        self.connect("download-completed", self.on_download_completed)
        self.connect("download-error", self.on_download_error)

    def on_download_initializing(self, song):
        print "[Download connecting]", self.get_id()
        self.state = Song.STATE_CONNECTING

    def on_download_started(self, song):
        print "[Download started]", self.get_id()
        self.state = Song.STATE_DOWNLOADING

    def on_download_paused(self, song):
        print "[Download paused]", self.get_id()
        self.state = Song.STATE_PAUSED

    def on_download_canceled(self, song):
        print "[Download canceled]", self.get_id()
        self.state = Song.STATE_CANCELED

    def on_download_completed(self, song):
        print "[Download completed]", self.get_id()
        self.state = Song.STATE_COMPLETED

    def on_download_error(self, song, error):
        print "[Download error]", self.get_id(), error
        self.state = Song.STATE_ERROR
        self.last_error = error

    def __getitem__(self, key):
        """
        Allows to use the song as a dictionary (not recommended, use
        methods instead)
        """
        return self.data[key]

    def clone(self):
        """
        Clone the song but changes it local ID to avoid errors during the song searching
        on AbstractSongList
        """
        newsong = Song(self.get_data())
        if newsong.get_cover_pixbuf() == None:
            newsong.set_cover_pixbuf(self.get_cover_pixbuf())
        newsong.set_filename(self.get_filename())

        return newsong

    def equals(self, othersong):
        """
        Compare a song with another
        @param othersong: the song to compare
        """
        if othersong == None:
            return False

        return self.local_id == othersong.local_id

    def get_data(self):
        return self.data

    def get_state(self):
        return self.state

    def set_state(self, state):
        self.state = state

    def get_id(self):
        return self.data['SongID']

    def get_title(self):
        return self.data['SongName']

    def get_album(self):
        return self.data['AlbumName']

    def get_artist(self):
        return self.data['ArtistName']

    def get_track_num(self):
        return self.data['TrackNum']

    def get_year(self):
        return self.data['Year']

    def get_duration(self):
        return self.data['EstimateDuration']

    @staticmethod
    def format_time(dur):
        duration = float(dur)
        mins = math.floor(duration / 60)
        secs = duration % 60

        return "%02d:%02d" % (mins, secs)

    def get_duration_human_readable(self):
        return Song.format_time(self.get_duration()) 

    def get_last_error(self):
        return self.last_error

    def get_cover_filename(self):
        return self.data['CoverArtFilename']

    def get_cover_pixbuf(self):
        """
        Get the pixbuf for the song album cover.
        If returns None, means that we need to download the cover
        using download_cover
        """
        if self.cover_pixbuf == None:
            if self.get_cover_filename() == "":
                self.set_cover_missed_pixbuf()
            else:
                self.set_cover_cached_pixbuf()
        return self.cover_pixbuf

    def set_cover_pixbuf(self, pixbuf):
        """
        Set the pixbuf for the song album cover.
        Used by SongCoverThread and clone.
        """
        self.cover_pixbuf = pixbuf

    def set_cover_missed_pixbuf(self):
        self.cover_pixbuf = covercache.get_missed_pixbuf()

    def set_cover_cached_pixbuf(self):
        self.cover_pixbuf = covercache.get_pixbuf(self)

    def download_cover(self):
        """
        Download the album cover, the object will emit the 'cover-downloaded'
        signal when the download finish.
        """
        self.cover_thread = SongCoverThread(self)
        self.cover_thread.start()

    def cancel_cover_download(self):
        if self.cover_thread != None:
            self.cover_thread.canceled.set()

    def start_download(self, restart = False, speed = None):
        """
        Starts the song download, the object will emit various signals to
        handle the download progress.
        @param restart: If is False means that we should try to continue with the
        download if file exists.
        @param speed: The speed limit for the download, the default is the confi-
        gured in the app.
        """
        if speed == None:
            speed = int(config()["speed_limit"]) * 1024

        self.download_thread = DownloadThread(self)
        self.download_thread.restart = restart
        self.download_thread.speed = speed
        self.download_thread.start()

    def is_downloading(self):
        """
        Returns true if the download is running
        """
        return self.download_thread != None and self.download_thread.is_alive()

    def is_paused(self):
        """
        Returns true if the download was stopped by pausing it
        """
        return self.download_thread != None and self.is_downloading() == False and self.download_thread.is_canceled == False

    def pause_download(self):
        """
        Pause the current download
        """
        if self.is_downloading():
            self.download_thread.pause()
        else:
            self.state = Song.STATE_PAUSED
            self.emit("download-paused")

    def cancel_download(self):
        """
        Cancel the current download
        """
        if self.is_downloading():
            self.download_thread.cancel()
        else:
            if self.state != Song.STATE_COMPLETED and os.path.exists(self.get_filename()):
                os.remove(self.get_filename())
            self.emit("download-canceled")

    def resume_download(self):
        """
        Resume the file download, the only difference with start_download is that
        this method checks wether the file is downloading, ignore the action
        in that case.
        """
        if self.is_downloading() == False and self.state != Song.STATE_COMPLETED:
            self.start_download(False)

    def reset_unfinished_download_state(self):
        if self.is_downloading() == False and self.state != Song.STATE_COMPLETED:
            self.set_state(Song.STATE_NOT_STARTED)

    def pause_download_sync(self):
        """
        Pause the current download and wait until it stops altogether.
        """
        if self.is_downloading():
            self.download_thread.pause()
            self.download_thread.join()

    def get_download_progress(self):
        """
        Returns the current download progress in bytes or None if
        the download is not initialized.
        """
        if self.download_thread != None:
            return self.download_thread.download_progress
        else:
            return None

    def get_file_size(self):
        """
        Returns the current file size in bytes or None if
        the download is not initialized.
        """
        if self.download_thread != None:
            return self.download_thread.file_size
        else:
            return None

    def get_download_speed(self):
        """
        Returns the current download speed in bytes per second
        the download is not initialized.
        """
        if self.download_thread != None:
            return self.download_thread.download_speed
        else:
            return None

    def get_filename(self):
        return self.filename

    def set_filename(self, value):
        self.filename = value

    def get_default_filename(self):
        pattern = config()['file_pattern'] + ".mp3"
        filename = pattern.format(artist = self.get_artist().strip("<>:\"/\|?&*"),
                                  song = self.get_title().strip("<>:\"/\|?&*"),
                                  album = self.get_album().strip("<>:\"/\|?&*"))
        filename = filename.replace('/', '-')
        filename = os.path.join(config()['down_path'], filename)

        return filename

    def get_streaming_url(self):
        try:
            key = groove.getStreamKeyFromSongIDEx(self.get_id())
        except Exception as e:
            print "[Streaming URL error]", e.__str__()
            raise e

        print "[Key for song streaming", self.get_id(), "]", key
        playurls = "http://%s/stream.php?streamKey=%s"
        play_url = playurls % (key["result"]["%s" % self.get_id()]["ip"],
                               key["result"]["%s" % self.get_id()]["streamKey"])

        return str(play_url)

gobject.type_register(Song)
"""
Signals of the Song type
"""
# Emitted when the cover download was finished
gobject.signal_new("cover-downloaded", Song, gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ())
# Emitted when download starts or resumes
gobject.signal_new("download-initializing", Song, gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ())
# Emitted when download starts or resumes
gobject.signal_new("download-started", Song, gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ())
# Emitted when cUrl receive data from GrooveShark (useful for update download progress)
gobject.signal_new("download-updated", Song, gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ())
# Emitted when the download is successfully downloaded
gobject.signal_new("download-completed", Song, gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ())
# Emitted when download is canceled
gobject.signal_new("download-canceled", Song, gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ())
# Emitted when download is paused
gobject.signal_new("download-paused", Song, gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ())
# Emitted when download is stopped
gobject.signal_new("download-stopped", Song, gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ())
# Emitted when a download error occurs, an error message is passed by parameter
gobject.signal_new("download-error", Song, gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_STRING,))


class SongCoverThread(threading.Thread):
    """
    This class download a song cover album and notify
    it when download ends. Should not be used directly, use Song instead.
    """

    concurrent_downloads = threading.Semaphore(5)
    internal_lock = threading.Semaphore()
    cancel_downloads = threading.Event()
    downloading_events = {}

    def __init__(self, song):
        threading.Thread.__init__(self)
        self.song = song
        self.canceled = threading.Event()

    def run(self):
        SongCoverThread.internal_lock.acquire()
        if self.song.get_cover_filename() in SongCoverThread.downloading_events:
            SongCoverThread.internal_lock.release()
            SongCoverThread.downloading_events[self.song.get_cover_filename()].wait()
            self.song.set_cover_cached_pixbuf()
            if self.song.cover_pixbuf == None:
                self.song.set_cover_missed_pixbuf()
            gobject.idle_add( self.song.emit, "cover-downloaded" )
            return
        else:
            SongCoverThread.downloading_events[self.song.get_cover_filename()] = threading.Event()
            SongCoverThread.internal_lock.release()

        groove.init()
        SongCoverThread.concurrent_downloads.acquire()

        if SongCoverThread.cancel_downloads.is_set() or self.canceled.is_set():
            SongCoverThread.concurrent_downloads.release()
            return

        try:
            url = "http://images.grooveshark.com/static/albums/90_%s" % self.song.get_cover_filename()
            print "[Downloading cover]", url

            conn = groove.createCurl(str(url))
            conn.set_timeout(10)

            try:
                os.makedirs(os.path.dirname(covercache.get_filename(self.song)))
            except:
                pass
            file = open(covercache.get_filename(self.song)+".incoming", "wb")
            conn.setopt(pycurl.WRITEDATA, file)

            loader = gtk.gdk.PixbufLoader()
            loader.write(conn.perform())
            loader.close()

            conn.close()
            file.close()
            os.rename(covercache.get_filename(self.song)+".incoming", covercache.get_filename(self.song))

            self.song.cover_pixbuf = loader.get_pixbuf()
        except Exception, e:
            print "Error while downloading cover: ", e
            self.song.set_cover_missed_pixbuf()
            if file.closed == False:
                file.close()
            try:
                os.remove(covercache.get_filename(self.song)+".incoming")
            except:
                pass

        SongCoverThread.concurrent_downloads.release()

        SongCoverThread.downloading_events[self.song.get_cover_filename()].set()
        del SongCoverThread.downloading_events[self.song.get_cover_filename()]
        gobject.idle_add( self.song.emit, "cover-downloaded" )


class DownloadThread(threading.Thread):
    """
    This class download the song file and notify the progress.
    Should not be used directly, use Song instead.
    """

    def __init__(self, song):
        threading.Thread.__init__(self)

        self.song = song
        self.restart = False
        self.speed = 0
        self.download_progress = None

        self.download_speed = None
        self.download_time_start = None
        self.download_size_on_start = None

        self.file_size = None
        self.resume_downloaded = 0

        self.first_hook = True
        self._stop = threading.Event()
        self.is_canceled = True
        self.file = None
        self.curl = None

    def run(self):
        self.song.emit("download-initializing")

        self.first_hook = True
        self._stop.clear()
        restart = self.restart

        if restart == False and os.path.exists(self.song.get_filename()) == False:
            restart = True

        try:
            if restart == True:
                self.file = open(self.song.get_filename(), "wb")
            else:
                self.file = open(self.song.get_filename(), "ab")
        except IOError:
            self.song.emit("download-error", _("Failed to create '%s' for writing.") % self.song.get_filename())
            return

        try:
            url = self.song.get_streaming_url()
            c = groove.createCurl(url)
            c.connect("header-downloaded", self.on_header)
            c.setopt(pycurl.NOPROGRESS, 0)
            c.setopt(pycurl.PROGRESSFUNCTION, self.hook)
            c.setopt(pycurl.WRITEDATA, self.file)
            c.set_timeout(0)
            c.set_return_transfer(False)
            if restart == False:
                self.resume_downloaded = os.path.getsize(self.song.get_filename())
                c.setopt(pycurl.RESUME_FROM, self.resume_downloaded)
            else:
                self.resume_downloaded = 0
            if self.speed != 0:
                c.setopt(pycurl.MAX_RECV_SPEED_LARGE, self.speed)

            c.perform()
            c.close()

            self.file.close()
            self.download_progress = 100
            self.song.emit("download-completed")
        except pycurl.error, e:
            self.file.close()
            if e[0] == pycurl.E_ABORTED_BY_CALLBACK:
                if self.is_canceled == True:
                    os.remove(self.song.get_filename())
                    self.song.emit("download-canceled")
                else:
                    self.song.emit("download-paused")
            else:
                os.remove(self.song.get_filename())
                self.song.emit("download-error", e[1])
        except Exception, e:
            self.file.close()
            os.remove(self.song.get_filename())
            self.song.emit("download-error", e.__str__())
            return

        self.song.emit("download-stopped")

    def cancel(self):
        self.is_canceled = True
        self._stop.set()

    def pause(self):
        self.is_canceled = False
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()

    def on_header(self, c):
        # If is not partial content (partial content is status code 206)
        if c.get_status() == 200:
            self.file.truncate(0)

    def hook(self, downloadTotal, downloadCurrent, uploadTotal, uploadCurrent):
        if self.stopped():
            return True

        if downloadTotal > 0:
            if self.first_hook:
                self.first_hook = False
                self.song.emit("download-started")

            downloadTotal += self.resume_downloaded
            downloadCurrent += self.resume_downloaded

            progress = (downloadCurrent / downloadTotal) * 100
            self.download_progress = progress
            self.file_size = downloadTotal

            current_time = time.time()
            if current_time - self.download_time_start > 1:
                self.download_speed = downloadCurrent - self.resume_downloaded - self.download_size_on_start
                self.download_size_on_start = downloadCurrent - self.resume_downloaded
                self.download_time_start = current_time

            if progress <= 99:
                self.song.emit("download-updated")
        else:
            self.download_time_start = time.time()
            self.download_size_on_start = 0

        return False
