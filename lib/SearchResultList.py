from AbstractSongList import AbstractSongList
import gtk
import glib

class SearchResultList(AbstractSongList):
    """
    Represent the list of search results
    """

    def __init__(self, view):
        self.filter_text = ""
        self.modelfilter = None
        self.sortmodel = None

        AbstractSongList.__init__(self, view)

    def create_model(self):
        # Model: Song, Title, Artist, Album
        model = gtk.ListStore(object, str, str, str)
        self.modelfilter = model.filter_new()
        self.modelfilter.set_visible_func(self.filter_visible_func)
        return gtk.TreeModelSort(self.modelfilter)

    def append_song(self, song):
        self.get_full_model().append([
            song,
            glib.markup_escape_text(song.get_title()),
            song.get_artist(),
            song.get_album()
        ])

    def get_model(self):
        return self.modelfilter

    def get_sorted_model(self):
        return self.get_view().get_model()

    def get_full_model(self):
        return self.get_model().get_model()

    def clear(self):
        self.get_full_model().clear()

    def create_view(self):
        self.get_view().get_selection().set_mode(gtk.SELECTION_MULTIPLE)

        rendererText = gtk.CellRendererText()
        column = gtk.TreeViewColumn(_("Title"), rendererText, markup = 1)
        self.get_view().append_column(column)
        column.set_resizable(True)
        column.set_max_width(300)
        column.set_sort_column_id(1)

        column = gtk.TreeViewColumn(_("Artist"), rendererText, text = 2)
        self.get_view().append_column(column)
        column.set_resizable(True)
        column.set_sort_column_id(2)

        column = gtk.TreeViewColumn(_("Album"), rendererText, text = 3)
        self.get_view().append_column(column)
        column.set_resizable(True)
        column.set_max_width(150)
        column.set_sort_column_id(3)

    def set_filter_text(self, text):
        self.filter_text = " ".join(text.split()).lower()
        self.modelfilter.refilter()

    def get_filter_text(self, text):
        return self.filter_text

    def filter_visible_func(self, model, iter):
        if self.filter_text == "":
            return True
        else:
            song = model[iter][0]
            t = self.filter_text
            return song.get_title().lower().find(t) >= 0 or song.get_artist().lower().find(t) >= 0 or song.get_album().lower().find(t) >= 0

    def get_selected_rows(self):
        selection = self.get_view().get_selection().get_selected_rows()[1]
        for i in range(len(selection)):
            selection[i] = self.get_sorted_model().convert_path_to_child_path(selection[i])
        return selection
