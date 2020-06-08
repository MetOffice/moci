#!/usr/bin/env bash

function cleanup () {
    rm *aux *dvi *log *pdf *toc
}

cleanup

#Run the build 3 times to make sure any references etc are realised
for i in `seq 1 3`; do
    latex README.tex
done

if [ ! -f "README.dvi" ]; then
    echo "The documentation has not built correctly, please check LaTeX output"
    exit 999
fi

dvipdf README.dvi README.pdf
cp README.pdf ../
cleanup

