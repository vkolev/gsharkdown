import gtk
import gobject
from enviroment import config, env
from PlayList import PlayList

class PlayListStyleWidget(gtk.Button):
    def __init__(self):
        gtk.Button.__init__(self)

        self.menu = gtk.Menu()

        menu_items = [
            (PlayList.TEXT_BELOW_ICONS, _("Text below icons"),),
            (PlayList.TEXT_BESIDE_ICONS, _("Text beside icons"),),
#            (PlayList.ICONS_BIG, _("Icons only (big)"),),
#            (PlayList.ICONS_SMALL, _("Icons only (small)"),),
            (PlayList.NOT_SHOW, _("Not show"),),
        ]

        first_item_widget = None

        for item in menu_items:
            item_widget = gtk.RadioMenuItem(None, item[1])
            if first_item_widget == None:
                first_item_widget = item_widget
            else:
                item_widget.set_group(first_item_widget)
            self.menu.append(item_widget)

            if item[0] == str(config()["playlist_style"]):
                item_widget.set_active(True)

            item_widget.connect("activate", self.on_item_activate, item[0])

        self.menu.show_all()
        self.set_image(gtk.image_new_from_file("%s/data/playlist_style.png" % env().BASEPATH))
        self.set_relief(gtk.RELIEF_NONE)
        self.set_focus_on_click(False)

        if env().have_playlist_style() == True:
            self.connect("clicked", self.on_clicked)
            self.set_tooltip_text(_("Change the playlist style"))
        else:
            self.set_sensitive(False)
            self.set_tooltip_text(_("Please update your version of PyGtk\nto change the playlist style"))

    def on_clicked(self, button):
        self.menu.popup(None, None, self.menu_reposition_callback, 0, 0)

    def menu_reposition_callback(self, menu, data = None):
        return (
            self.get_parent_window().get_origin()[0] + self.get_allocation().x,
            self.get_parent_window().get_origin()[1] + self.get_allocation().y + self.get_allocation().height - 5,
            True
        )

    def on_item_activate(self, menuitem, style):
        if menuitem.get_active() == True:
            config()["playlist_style"] = style
            config().write()
            self.emit("style-changed", style)


gobject.type_register(PlayListStyleWidget)
gobject.signal_new("style-changed", PlayListStyleWidget, gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_STRING,))
