import httplib
import StringIO
import hashlib
import uuid
import random
import string
import sys
import gzip
import pycurl
import ipycurl
import threading
import time
import gobject
from enviroment import env

if sys.version_info[1] >= 6:
    import json

def dummy(error = None):
    pass

_referer = "http://grooveshark.com/JSQueue.swf?20120312.08"
_token = None
_isInitialized = False
_initializingLock = threading.Lock()
_onInitError = dummy
_onInitStart = dummy
_onInitFinish = dummy
_initFailed = False

h = {}
h["country"] = {}
h["country"]["CC1"] = "72057594037927940"
h["country"]["CC2"] = "0"
h["country"]["CC3"] = "0"
h["country"]["IPR"] = "1"
h["country"]["CC4"] = "0"
h["country"]["ID"] = "57"
h["privacy"] = 0
h["session"] = None
h["uuid"] = str.upper(str(uuid.uuid4()))

entrystring = \
"""A Grooveshark song downloader in python
by George Stephanos <gaf.stephanos@gmail.com>
"""

def createCurl(url = None):
    """
    Create a configurated cURL object
    """
    c = ipycurl.Curl(url)
    c.setopt(pycurl.USERAGENT, env().USER_AGENT)
    c.set_option(pycurl.FAILONERROR, True)

    c.setopt(pycurl.COOKIEFILE, env().get_config_directory() + "/cookie.txt")
    c.setopt(pycurl.COOKIEJAR, env().get_config_directory() + "/cookie.txt")
    c.set_timeout(50)

    proxy = env().get_proxy()
    if proxy != None:
        c.setopt(pycurl.PROXY, proxy["host"])
        c.setopt(pycurl.PROXYPORT, int(proxy["port"]))
        if proxy["user"] != None:
            c.setopt(pycurl.PROXYUSERPWD, proxy["user"] + ":" + proxy["pass"])
    else:
        c.setopt(pycurl.PROXY, "")

    return c

def prepToken(method, sectoken):
    """
    Method to create the tocken for the request.
    """
    rnd = (''.join(random.choice(string.hexdigits) for x in range(6))).lower()
    hashs = hashlib.sha1(
        method + ":" + _token + sectoken + rnd).hexdigest()
    ret = rnd + hashs
    return ret


def getToken():
    """
    Gets a token from the grooveshark.com service
    """
    global h, _token
    p = {}
    p["parameters"] = {}
    p["parameters"]["secretKey"] = hashlib.md5(h["session"]).hexdigest()
    p["method"] = "getCommunicationToken"
    p["header"] = h
    p["header"]["client"] = "htmlshark"
    p["header"]["clientRevision"] = "20120312"

    conn = createCurl("https://grooveshark.com/more.php?" + p["method"])
    conn.setopt(pycurl.POST, True)
    conn.setopt(pycurl.POSTFIELDS, json.JSONEncoder().encode(p))
    conn.setopt(pycurl.HTTPHEADER, [
        "Referer: " + _referer,
        "Accept-Encoding: gzip",
        "Content-Type: application/json"
    ])
    resp = conn.perform()
    conn.close()

    gzipfile = gzip.GzipFile(fileobj = (StringIO.StringIO(resp)))
    _token = json.JSONDecoder().decode(gzipfile.read())["result"]


def getSearchResultsEx(query, _type = "Songs"):
    """
    Method to get the search results from the gs service
    and returns them as dictionary.
    """
    init()

    p = {}
    p["parameters"] = {}
    p["parameters"]["type"] = _type
    p["parameters"]["query"] = query
    p["header"] = h
    p["header"]["client"] = "htmlshark"
    p["header"]["clientRevision"] = "20120312"
    p["header"]["token"] = prepToken("getResultsFromSearch", ":reallyHotSauce:")
    p["method"] = "getResultsFromSearch"

    conn = createCurl("https://grooveshark.com/more.php?" + p["method"])
    conn.setopt(pycurl.POST, True)
    conn.setopt(pycurl.POSTFIELDS, json.JSONEncoder().encode(p))
    conn.setopt(pycurl.HTTPHEADER, [
        "Referer: http://grooveshark.com/",
        "Accept-Encoding: gzip",
        "Content-Type: application/json"
    ])
    resp = conn.perform()
    conn.close()

    gzipfile = gzip.GzipFile(fileobj = (StringIO.StringIO(resp)))
    j = json.JSONDecoder().decode(gzipfile.read())
    result = j['result']['result']
    if hasattr(result, 'Songs'):
        return result['Songs']
    else:
        return result


def getStreamKeyFromSongIDEx(_id):
    """
    Gets the stream URL for Song ID
    """
    init()

    p = {}
    p["parameters"] = {}
    p["parameters"]["mobile"] = "false"
    p["parameters"]["prefetch"] = "false"
    p["parameters"]["songIDs"] = _id
    p["parameters"]["country"] = h["country"]
    p["header"] = h
    p["header"]["client"] = "jsqueue"
    p["header"]["clientRevision"] = "20120312.08"
    p["header"]["token"] = prepToken("getStreamKeysFromSongIDs", ":circlesAndSquares:")
    p["method"] = "getStreamKeysFromSongIDs"

    conn = createCurl("https://grooveshark.com/more.php?" + p["method"])
    conn.setopt(pycurl.POST, True)
    conn.setopt(pycurl.POSTFIELDS, json.JSONEncoder().encode(p))
    conn.setopt(pycurl.HTTPHEADER, [
        "Referer: " + _referer,
        "Accept-Encoding: gzip",
        "Content-Type: application/json"
    ])
    resp = conn.perform()
    conn.close()

    gzipfile = gzip.GzipFile(fileobj = (StringIO.StringIO(resp)))
    j = json.JSONDecoder().decode(gzipfile.read())

    if len(j["result"][str(_id)]) == 0:
        raise Exception("The song streaming key is empty")

    return j


def init():
    global _isInitialized, _initFailed

    _initializingLock.acquire()
    if isInitialized():
        _initializingLock.release()
        if _initFailed == True:
            raise Exception(_("Grooveshark is not initialized"))
        return

    print "[Initializing Grooveshark]"
    gobject.idle_add(_onInitStart)
    while True:
        try:
            conn = createCurl("http://grooveshark.com/")
            conn.perform()

            cookielist = conn.get_info(pycurl.INFO_COOKIELIST)
            for cookie in cookielist:
                cookie = cookie.split("\t")
                if cookie[5] == "PHPSESSID":
                    h["session"] = cookie[6]

            conn.close()
            getToken()
            print "[Grooveshark initialized]"
            break
        except Exception as e:
            if e.args[0] == 11004:
                time.sleep(1)
            else:
                print "[Grooveshark initialized failed]"
                _initFailed = True
                gobject.idle_add(_onInitError, e.__str__())
                break

    _isInitialized = True
    _initializingLock.release()
    gobject.idle_add(_onInitFinish)

    if _initFailed == True:
        raise Exception(_("Grooveshark is not initialized"))

def onInitError(callback):
    global _onInitError
    _onInitError = callback

def onInitStart(callback):
    global _onInitStart
    _onInitStart = callback

def onInitFinish(callback):
    global _onInitFinish
    _onInitFinish = callback

def isInitialized():
    return _isInitialized

def getSession():
    return h["session"]
