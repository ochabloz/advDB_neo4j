#!/bin/bash

DBLP_ARCHIVE_URL=${DBLP_ARCHIVE_URL:-'https://originalstatic.aminer.cn/misc/dblp.v13.7z'}
DL_FILE="/data/dblp.7z"


if [[ $DBLP_ARCHIVE_URL == *.7z ]]; then
    if [ ! -f "$DL_FILE" ]; then
        wget $DBLP_ARCHIVE_URL -O $DL_FILE
    else
        sleep 30
    fi

    7zz x $DL_FILE -so \
        | sed -E 's/NumberInt\(([0-9]+)\)/\1/' \
        | jq -c --stream 'fromstream(1|truncate_stream(inputs))' \
        | python3 dblp_importer.py
elif [[ $DBLP_ARCHIVE_URL == *.json ]]; then
    sleep 30
    wget $DBLP_ARCHIVE_URL -O - \
        | sed -E 's/NumberInt\(([0-9]+)\)/\1/' \
        | jq -c --stream 'fromstream(1|truncate_stream(inputs))' \
        | python3 dblp_importer.py
fi

echo "Containers job complete"
sleep infinity
