import os
import gtk
from enviroment import env, config

_missed_pixbuf = None
_mem_cache = {}

def get_filename(song):
    if song.get_cover_filename() == "":
        return None
    else:
        return os.path.join(env().get_config_directory(), "covers", song.get_cover_filename())

def get_pixbuf(song):
    global _mem_cache

    fname = get_filename(song)
    if fname in _mem_cache:
        return _mem_cache[fname]

    if os.path.exists(fname):
        with file(fname, 'a'):
            os.utime(fname, None)
        _mem_cache[fname] = gtk.gdk.pixbuf_new_from_file(fname)
        return _mem_cache[fname]
    else:
        return None

def get_missed_pixbuf():
    global _missed_pixbuf
    if _missed_pixbuf == None:
        _missed_pixbuf = gtk.gdk.pixbuf_new_from_file("%s/data/sdefault.png" % env().BASEPATH)
    return _missed_pixbuf

def analyze_cache_limit():
    filelist = os.listdir(os.path.join(env().get_config_directory(), "covers"))
    filelist_full = []
    totalsize = 0
    limitsize = int(config()["cover_cache_limit"])

    for f in filelist:
        fname = os.path.join(env().get_config_directory(), "covers", f)
        fstat = os.stat(fname)

        filelist_full.append((fname, fstat.st_atime, fstat.st_size))
        totalsize += fstat.st_size

    if totalsize > limitsize:
        filelist_full = sorted(filelist_full, key = lambda file: file[1])
        i = 0
        while totalsize > limitsize:
            file = filelist_full[i]
            totalsize -= file[2]
            os.remove(file[0])
            i += 1
