#!/usr/bin/env python
#-*- encoding: utf-8 -*-

import urllib2
from xml.etree import ElementTree
import sys
import os

"""
A simple library for searching lyrics in the lyrdb
and the chartlyrics webservices.
"""

__doc__ = """Lyrbrary to work with the lyrdb and chartlyrics webservices"""
__author__ = "Vladimir Kolev <vladimir.r.kolev@gmail.com>"
__version__ = 1.0
__license__ = "GNU General Public License v.3"

LOOKUP_URL = "http://webservices.lyrdb.com/lookup.php?q=%s&for=%s&agent=gSharkDown"
GETLYR_URL = "http://webservices.lyrdb.com/getlyr.php?q=%s"
CHART_URL = "http://api.chartlyrics.com/apiv1.asmx/SearchLyricDirect?artist=%s&song=%s"

basepath = os.path.abspath(os.path.dirname(sys.argv[0]).strip("/lib"))

def search(artist, track, method = "match"):
    """
    Executes the 2 search methods in a row trying to 
    find lyrics for the desired artist and track.
    """
    first = searchlyr(artist, track, method)
    if "error" in first:
        second = searchchart(artist, track)
        if "error" in second:
            lyrics = "ERROR: Cant't find lyrics for {artist} - {track}".format(artist = artist,
                                                               track = track)
        else:
            lyrics = second
    else:
        lyrics = getlyrics(first)

    return lyrics


def getlyrics(songid):
    """
    Retrieves the lyrics text from the lyrdb webserice
    with gives songid as parameter.
    """
    req = urllib2.urlopen(GETLYR_URL % songid)
    lyric = req.read()
    return lyric

def searchlyr(artist, track, method):
    """
    Searches the lyrdb webservice and returns the songID in the
    lyrdb webservice
    Accepts the following parameters:
    @param artist : The song artist as string
    @param track : The song name as string
    @param method : The method to search with, could be 'trackname',
                    'artist', 'fullt
    """
    query = artist.replace(" ", "+")
    query += "|"
    query += track.replace(" ", "+")

    if method == "trackname":
        query = track.replace(" ", "+")
    elif method == "artist":
        query = artist.replace(" ", "+")
    elif method == "fullt":
        query = artist.replace(" ", "+")
        query += "+"
        query += track.replace(" ", "+")
    try:
        req = urllib2.urlopen(LOOKUP_URL % (query, method))
        result = req.read()
        resp = ""
        if "error" in result:
            resp = "error"
        elif result == "":
            resp = "error"
        else:
            t = result.splitlines()
            resp = t[0].split("\\")[0]
    except:
        resp = "error"
    return resp

def searchchart(artist, track):
    """
    Searches the Chartlyrics and returns the lyrics if found
    Accepts the following parameters:
    @param artist : The song artist as string
    @param track : The song track as string
    """
    artist = artist.replace(" ", "%20")
    track = track.replace(" ", "%20")
    try:
        req = urllib2.urlopen(CHART_URL % (artist, track))
        result = req.read()
        resp = ""
        if "<LyricChecksum>" in result:
            lyric = ElementTree.fromstring(result)
            lyr = lyric.getchildren()[len(lyric.getchildren()) - 1]
            resp = lyr.text
        else:
            resp = "error"
    except:
        resp = "error"
    return resp
