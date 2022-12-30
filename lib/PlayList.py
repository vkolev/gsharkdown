from AbstractSongList import AbstractSongList
from enviroment import env, config
import gtk
import glib

class PlayList (AbstractSongList):
    """
    Represent the PlayList
    """

    # Styles
    TEXT_BELOW_ICONS = "0"
    TEXT_BESIDE_ICONS = "1"
    ICONS_BIG = "2"
    ICONS_SMALL = "3"
    NOT_SHOW = "4"

    ICON_SIZE = 80

    def __init__(self, view):
        self.style = PlayList.TEXT_BELOW_ICONS
        AbstractSongList.__init__(self, view)
        self.playing_song = None

    def create_model(self):
        # Model: Song, Full label, Sliced label, Big image, Small image, Tooltip
        return gtk.ListStore(object, str, str, gtk.gdk.Pixbuf, gtk.gdk.Pixbuf, str)

    def get_sliced_string(self, str, max):
        sliced = str[0:max - 3]
        if len(sliced) < len(str):
            return sliced + "..."
        else:
            return str

    def create_view(self):
        self.get_view().set_selection_mode(gtk.SELECTION_MULTIPLE)
        self.get_view().set_reorderable(True)
        self.get_view().set_columns(99999)

        self.get_view().add_events(gtk.gdk.SCROLL_MASK)
        self.get_view().connect("scroll-event", self.on_mouse_wheel_scroll)

        self.set_style(config()["playlist_style"])

    def on_mouse_wheel_scroll(self, widget, event):
        # We need to assume that the IconView has a ScrolledWindow as parent 
        adjustment = self.get_view().get_parent().get_hadjustment()
        if event.direction == gtk.gdk.SCROLL_UP:
            newvalue = adjustment.get_value() - adjustment.get_step_increment()
            if newvalue < 0:
                newvalue = 0
        else:
            newvalue = adjustment.get_value() + adjustment.get_step_increment()
            if newvalue > adjustment.get_upper() - adjustment.get_page_size():
                newvalue = adjustment.get_upper() - adjustment.get_page_size()
        adjustment.set_value(newvalue)

    def set_style(self, style):
        self.style = style

        self.get_view().set_tooltip_column(5)

        if style == PlayList.TEXT_BELOW_ICONS:
            self.get_view().set_markup_column(2)
            self.get_view().set_pixbuf_column(3)
            if env().have_playlist_style():
                self.get_view().set_item_orientation(gtk.ORIENTATION_VERTICAL)
            self.get_view().set_spacing(0)
            self.get_view().set_item_width(90)
        elif style == PlayList.TEXT_BESIDE_ICONS:
            self.get_view().set_markup_column(1)
            self.get_view().set_pixbuf_column(4)
            if env().have_playlist_style():
                self.get_view().set_item_orientation(gtk.ORIENTATION_HORIZONTAL)
            self.get_view().set_spacing(5)
            self.get_view().set_item_width(150)
        elif style == PlayList.ICONS_BIG:
            self.get_view().set_markup_column(-1)
            self.get_view().set_pixbuf_column(3)
            if env().have_playlist_style():
                self.get_view().set_item_orientation(gtk.ORIENTATION_VERTICAL)
            self.get_view().set_spacing(0)
            self.get_view().set_item_width(90)
        elif style == PlayList.ICONS_SMALL:
            self.get_view().set_markup_column(-1)
            self.get_view().set_pixbuf_column(4)
            if env().have_playlist_style():
                self.get_view().set_item_orientation(gtk.ORIENTATION_VERTICAL)
            self.get_view().set_spacing(0)
            self.get_view().set_item_width(60)

        if style == PlayList.NOT_SHOW:
            self.get_view().get_parent().get_parent().hide()
            self.get_view().unselect_all()
        else:
            self.get_view().get_parent().get_parent().show()

    def get_style(self):
        return self.style

    def get_selected_rows(self):
        return self.get_view().get_selected_items()

    def get_playing_song(self):
        """
        Returns the current playing song or None if not playing nothing.
        """
        return self.playing_song

    def reload_image(self, path_or_iter):
        song = self.get_song(path_or_iter)
        pixbuf = None

        if song.get_cover_pixbuf() != None:
            pixbuf = self.create_cornered_image(song.get_cover_pixbuf())
        else:
            pixbuf = self.create_loading_track_icon()

        if self.playing_song != None and song.equals(self.playing_song):
            pixbuf = self.create_play_image(pixbuf)

        self.get_model()[path_or_iter][3] = self.scale_big(pixbuf)
        self.get_model()[path_or_iter][4] = self.scale_small(pixbuf)

    def set_playing_song(self, song):
        """
        Set the current playing song.
        @param song: The song or None to indicate that there is no song playing
        """
        old_playing_song = self.playing_song
        self.playing_song = song

        if old_playing_song != None:
            self.reload_image(self.get_song_path(old_playing_song))

        if song != None:
            path = self.get_song_path(song)
            self.reload_image(path)
            self.get_view().scroll_to_path(path, False, 0, 0)


    def append_song(self, song):
        # Change song local ID to fix the search by song
        song = song.clone()

        song_string_full = "<span font_size='small'>{title}</span>\n<span font_size='small' fgcolor='#555555'>{artist}</span>".format(
            title = glib.markup_escape_text(song.get_title()),
            artist = glib.markup_escape_text(song.get_artist())
        )

        song_string_sliced = "<span font_size='small'>{title}</span>\n<span font_size='small' fgcolor='#555555'>{artist}</span>".format(
            title = self.get_sliced_string(glib.markup_escape_text(song.get_title()), 25),
            artist = self.get_sliced_string(glib.markup_escape_text(song.get_artist()), 20)
        )

        tooltip = _("<b>Title:</b> {title}\n<b>Artist:</b> {artist}\n<b>Album:</b> {album}\n<b>Year:</b> {year}").format(
            title = glib.markup_escape_text(song.get_title()),
            artist = glib.markup_escape_text(song.get_artist()),
            album = glib.markup_escape_text(song.get_album()),
            year = song.get_year()
        )

        appended_iter = self.get_model().append([
            song,
            song_string_full,
            song_string_sliced,
            None,
            None,
            tooltip
        ])

        self.reload_image(appended_iter)

        if song.get_cover_pixbuf() == None:
            song.connect("cover-downloaded", self.on_song_cover_downloaded)
            song.download_cover()

    def on_song_cover_downloaded(self, song):
        self.reload_image(self.get_song_path(song))

    def create_loading_track_icon(self):
        return gtk.gdk.pixbuf_new_from_file("%s/data/loading.png" % env().BASEPATH)

    def create_cornered_image(self, pixbuf):
        pixbuf = pixbuf.copy()
        corners = gtk.gdk.pixbuf_new_from_file("%s/data/corners.png" % env().BASEPATH)
        corners.composite(pixbuf, 0, 0, pixbuf.props.width, pixbuf.props.height,
                          0, 0, 1.0, 1.0, gtk.gdk.INTERP_HYPER, 255)
        return pixbuf

    def create_play_image(self, pixbuf):
        """
        Composite play.png with the pixbuf
        """
        pixbuf = pixbuf.copy()
        play = gtk.gdk.pixbuf_new_from_file('%s/data/play.png' % env().BASEPATH)
        play.composite(pixbuf, 0, 0, pixbuf.props.width, pixbuf.props.height,
                          0, 0, 1.0, 1.0, gtk.gdk.INTERP_HYPER, 255)
        return pixbuf

    def scale_big(self, pixbuf):
        return pixbuf.scale_simple(80, 80, gtk.gdk.INTERP_HYPER)

    def scale_small(self, pixbuf):
        return pixbuf.scale_simple(50, 50, gtk.gdk.INTERP_HYPER)
