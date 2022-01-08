#!/bin/bash

if [ "$1" = "" ] ; then
	echo "Usage: $0 version"
	exit 1
fi

VER=${1}

if [ -z `echo $VER | grep '^[[[:digit:]]\.[[:digit:]][[:digit:]]$'` ] ; then
	echo "Version in wrong format - must be xx.yy eg. 3.10"
	exit 1
fi

E_VER=$(printf '%s\n' "$VER" | sed -e 's/[\/&]/\\&/g')

PKG_NAME=enigma2-plugin-extensions-csfdlite_${VER}_all.ipk
E_PKG_NAME=$(printf '%s\n' "$PKG_NAME" | sed -e 's/[\/&]/\\&/g')

sed -i "s/Version:\ .*/Version:\ $E_VER/" control/control
sed -i "s/soucasnaverze=.*/soucasnaverze=${E_VER}/" ../plugin.py

CUR_DIR=`pwd`

pushd ..
tar --transform 's,^./,usr/lib/enigma2/python/Plugins/Extensions/CSFDLite/,' --exclude-vcs --exclude-vcs-ignore --exclude=build --numeric-owner --group=0 --owner=0 -cf $CUR_DIR/data.tar ./*
popd

mkdir deb
pushd deb
tar -xf ../data.tar
mkdir DEBIAN
cp ../control/control DEBIAN/
popd
dpkg-deb -Zgzip -b deb `basename -s .ipk $PKG_NAME`.deb

rm $CUR_DIR/data.tar
rm -rf deb
cp `basename -s .ipk $PKG_NAME`.deb $PKG_NAME
