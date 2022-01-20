#!/bin/bash

if [ "$1" = "" ] ; then
	echo "Usage: $0 version"
	exit 1
fi

VER=${1}
regex="^[[:digit:]]+\.[[:digit:]]+$"
if ! [[ $VER =~ $regex ]]; then
	echo "Version in wrong format - must be xx.yy eg. 3.10"
	exit 1
fi

PKG_NAME=csfdlite_${VER}

cat > control/control << EOF
Package: enigma2-plugin-extensions-csfdlite
Version: $VER
Description: CSFDLite
Section: base
Priority: optional
Maintainer: https://github.com/skyjet18/enigma2-plugin-extensions-csfdlite
Architecture:all
Homepage: unknown
Source: none
Description: Enigma2 CSFD lite plugin, $VER
EOF

cd ../
rm -rf package
mkdir package
cd package
tar -C ../src/ -czf data.tar.gz .
tar -C ../build/control -czf control.tar.gz .
cat "2.0" > debian-binary

ls -la
ar -r ${PKG_NAME}.ipk ./debian-binary ./control.tar.gz ./data.tar.gz
ar -r ${PKG_NAME}.deb ./debian-binary ./control.tar.gz ./data.tar.gz
cp -r csfdlite_* ../releases
cd ../
rm -rf package
tar -C src/ -czf releases/csfdlite_$VER.tar.gz .