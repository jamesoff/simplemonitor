#!/bin/bash

set -eu

VERSION=$1
BUILDDIR=simplemonitor-$VERSION

if [ -z "$VERSION" ]; then
	echo Missing version parameter
	exit 1
fi

cd build

[ -d $BUILDDIR ] && rm -rf $BUILDDIR
mkdir $BUILDDIR

echo "--> Copying files"

cp -v ../*.py ../monitor.sql ../LICENCE ../README.md ../CHANGELOG $BUILDDIR
cp -rv ../Monitors ../Alerters ../Loggers ../html $BUILDDIR

echo
echo "--> Tidying up"
find $BUILDDIR -name *.pyc -delete

echo
echo "--> Creating archives"
tar cjf ${BUILDDIR}.tar.gz $BUILDDIR
zip -r ${BUILDDIR}.zip $BUILDDIR

