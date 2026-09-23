#!/bin/bash
cd "$(dirname "$0")"
/usr/bin/python3 -m pubmed_fulltext.webapp &
SERVER_PID=$!
sleep 1.5
open http://127.0.0.1:5000
wait $SERVER_PID
