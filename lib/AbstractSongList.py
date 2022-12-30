import gtk
import gobject

class AbstractSongList(gobject.GObject):
    """
    This class represents a Song list linked with a TreeView  
    and a ListStore. also provides several facilities to manage the list.
    """

    def __init__(self, view):
        """
        Initialize the List
        @param view: The TreeView used in the list.
        """
        self._view = view
        self._view.set_model(self.create_model())
        self.create_view()

    def create_model(self):
        """
        Return the model used by the list, a derived class must reimplement
        this method.
        """
        model = gtk.ListStore(object)
        return model

    def create_view(self):
        """
        Initialize the TreeView, a derived class must reimplement
        this method.
        """
        pass

    def get_view(self):
        return self._view

    def get_model(self):
        return self.get_view().get_model()

    def append_song(self, song):
        """
        Append a song to the list, a derived class must reimplement
        this method.
        """
        self.get_model().append([song])

    def find_song(self, song):
        """
        Return a tuple containing the path and iter for the song passed
        by parameter or None if the song is not found.
        """
        iter = self.get_model().get_iter_first()
        while iter != None:
            if self.get_model()[iter][0].equals(song):
                return (self.get_model().get_path(iter), iter)
            iter = self.get_model().iter_next(iter)

        return None

    def get_song_row(self, song):
        """
        Returns the model row related to the song passed by parameter.
        """
        iter = self.get_song_iter(song)
        if iter == None:
            return None
        else:
            return self.get_model()[iter]

    def get_song_path(self, song):
        """
        Returns the path related to the song passed by parameter.
        """
        finded = self.find_song(song)

        if finded == None:
            return None
        else:
            return finded[0]

    def get_song_iter(self, song):
        """
        Returns the TreeIter related to the song passed by parameter.
        """
        finded = self.find_song(song)

        if finded == None:
            return None
        else:
            return finded[1]

    def get_song(self, path_or_iter):
        """
        Returns the song related to a path or iter
        """
        return self.get_model()[path_or_iter][0]


    # Shortcuts to handle the list

    def clear(self):
        """
        Clear the list.
        """
        self.get_model().clear()

    def __len__(self):
        """
        Allows to do the following: len(songlist)
        """
        return len(self.get_model())

    def first(self):
        """
        Returns the first iter of the list.
        """
        return self.get_model().get_iter_first()

    def next(self, iter):
        """
        Returns the next iter of the iter passed by parameter
        """
        return self.get_model().iter_next(iter)

    def range(self):
        """
        Returns a range from 0 to len-1 to ease the list walking.
        """
        return range(len(self.get_model()))

    def get_selected_rows(self):
        return self.get_view().get_selection().get_selected_rows()[1]

