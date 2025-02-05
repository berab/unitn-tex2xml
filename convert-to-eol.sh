#!/bin/bash

declare -a FILES=(
    0-general
    1-mcus
    2-code
    3-rtos
    4-sensors
    hassan
    beran-questions
)

if [ "$#" -ne 1 ]; then
    >&2 echo "Usage: $0 EXAM_TITLE"
    exit -1
fi

EXAM_TITLE=$1

rm -rf xml_files/*
mkdir -p xml_files

for FILE in "${FILES[@]}"
do
    echo "Converting $FILE".tex
    python3 convert-to-eol.py -f tex_files/${FILE} -t $EXAM_TITLE
    mv -f ${FILE}.xml xml_files

done
