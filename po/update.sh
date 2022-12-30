#!/bin/bash

if [ $(basename $PWD) != "po" ]
then
	echo "You must to execute this script using po directory as working directory"
	exit 1
fi

intltool-update -p -g gsharkdown

for F in $(find -regex ".*\.po" -printf "%f ")
do
	LANG=$(echo $F | cut -d "." -f 1)
	echo -n "Merging $F: "
	intltool-update -g gsharkdown "$LANG"
	echo
done
