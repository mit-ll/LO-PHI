#!/usr/bin/env bash
scriptPath=$(dirname $0)
cd $scriptPath

for dist in debs/*
do
    cd $dist

    for release in *.changes
    do
        yes | debsign -kcspensky@cs.ucsb.edu $release
        yes | dput ppa:cspensky/lophi $release
    done

    cd ../..
done