#!/bin/bash
# Symlink everything, create foldes if necessary

qtileconfig=$(pwd)

mkdir -p ~/.config/qtile

for file in ${qtileconfig}/*; do 
    if [[ "${file##*/}" == *.py ]]
    then ln -s ${file} ~/.config/qtile/
    fi 
done
