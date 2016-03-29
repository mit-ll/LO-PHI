#!/usr/bin/env bash
scriptPath=$(dirname $0)
cd $scriptPath

modules="lophi-automation lophi-analyzeMFT lophi-disk-introspection-server
lophi-net-services python-lophi python-lophi-semanticgap
python-lophi-volatility"

mkdir -p debs

for dist in $modules
do
    mkdir -p debs/$dist
    mv debs/$dist/* .

    cd $dist
    debuild --preserve-env clean
    dpkg-source --commit
    yes | debuild --preserve-env -S -kcspensky@cs.ucsb.edu -j4
    debuild --preserve-env clean
    cd ..

    mv *.deb debs/$dist/
    mv *.build debs/$dist/
    mv *.changes debs/$dist/
    mv *.dsc debs/$dist/
    mv *.gz debs/$dist/
    mv *.upload debs/$dist/

done