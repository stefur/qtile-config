#!/bin/bash
# Symlink everything, create folders if necessary

qtileconfig=$(pwd)

mkdir -p ~/.config/qtile

for file in ${qtileconfig}/*; do 
    if [[ "${file##*/}" == *.py ]]
    then ln -s ${file} ~/.config/qtile/
    fi 
done
