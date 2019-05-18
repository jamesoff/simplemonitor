#!/bin/bash

set -eu

VERSION="${1?Missing version parameter}"
BUILDDIR=simplemonitor-$VERSION

cd build

[ -d "$BUILDDIR" ] && rm -rf "$BUILDDIR"
mkdir "$BUILDDIR"

echo "--> Copying files"

cp -v \
	../*.py \
	../LICENCE \
	../README.md \
	../CHANGELOG \
	"$BUILDDIR"
cp -rv \
	../Monitors \
	../Alerters \
	../Loggers \
	../html \
	../docker \
	"$BUILDDIR"

echo
echo "--> Tidying up"
find "$BUILDDIR" -name '*.pyc' -delete

echo
echo "--> Creating archives"
tar cjf "${BUILDDIR}.tar.gz" "$BUILDDIR"
zip -r "${BUILDDIR}.zip" "$BUILDDIR"

