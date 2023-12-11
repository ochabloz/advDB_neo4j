#!/bin/bash

DBLP_ARCHIVE_URL=${DBLP_ARCHIVE_URL:-'https://originalstatic.aminer.cn/misc/dblp.v13.7z'}
DL_FILE="/data/dblp.7z"

if [ ! -f "$DL_FILE" ]; then
    wget $DBLP_ARCHIVE_URL -O $DL_FILE
fi

7zz x $DL_FILE -so \
    | sed -E 's/NumberInt\(([0-9]+)\)/\1/' \
    | jq -c --stream 'fromstream(1|truncate_stream(inputs))' \
    | python3 dblp_importer.py

echo "Containers job complete"
sleep infinity
