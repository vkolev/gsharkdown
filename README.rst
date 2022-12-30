.. -*- restructuredtext -*-

gSharkDown
==========

It is a easy to use GNOME Desktop application for playing and
downloading audio files from the grooveshark audioservice. 

.. image:: http://i.imgur.com/je5bz.png

Post your opinion and suggestions here: http://gsharkdown.userecho.com/

Features
========

Some of the importart features:
    - GNOME Desktop integration
    - Ease to use
    - Playlist with loop option
    - Song information with album picture
    - Remembers the playlist on exit
    - Notifications on track change *(disabled by default)*
    - Multimedia Keys support under GNOME Desktop
    - Saving/Opening playlist in own format
    - Searching for Lyrics in two services: lyrdb and chartlyrics
    - Last.FM scrobbling *(disabled by default)*
    - Reordable playlist (thanks to eagleoneraptor)
    - Multiple items add to playlist (thanks to eagleoneraptor)
    - Multiple downloads (thanks to eagleoneraptor)
    

Dependenices
============

gSharkDown depends on the following libraries:
    - pygtk2 (python-gtk2 == 2.18)
    - ConfigObj (python-configobj)
    - python-gobject
    - python-gstreamer0.10
    - pycurl (since gsd version 0.4)
    - pynotofy (python-notify)
    - pylast (for the Last.FM scrobbling)
    - xdg-user-dirs
    - python-appindicator (>= 0.0.19)

Downloading for your Distribution
=================================

For Ubuntu/Debian:

You can use the provided packages in the Downloads section or just add the 
lffl PPA:

**For Ubuntu**

    sudo add-apt-repository ppa:ferramroberto/gsharkdown

    sudo apt-get update

    sudo apt-get install gsharkdown


**For Deabin**

    sudo echo "deb http://ppa.launchpad.net/ferramroberto/gsharkdown/ubuntu lucid main " | sudo tee -a /etc/apt/sources.list

    sudo apt-key adv --recv-keys --keyserver keyserver.ubuntu.com --recv-key 0xb725097b3acc3965

    sudo apt-get update 

    sudo apt-get install gsharkdown \\



**For ArchLinux:**

    There are 2 AUR packages one is the default and gsharkdown-lite removed the pylast dependency `gsharkdown <http://aur.archlinux.org/packages.php?O=0&K=gsharkdown&do_Search=Go>`_

**For Fedora/openSUSE** and other RPM based distributions:

    gSharkDown needs to be packaged for RPM based distributions, if you would like to package it, or already have made such repository please contact us to add it in the project


Licenses and Thanks
===================

gSharkDown is licensed under the GNU GPL v.3 License

The groove.py library is part of the groove-dl application from
jacktheripper51 (George Stephanos) and can be found at github on the following
webaddress: `groove-dl@github <https://github.com/jacktheripper51/groove-dl>`_

Special thanks to Damián Nohales for his commits.
Special thanks to speps for the patches
Special thanks to Ragi for the patch fixing multiple download crash

Any comments and help are welcome
