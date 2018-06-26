#!/bin/bash
cd `dirname $0`; source venv
python -m bkgen.project build-epub "$1" >output-epub.log 2>&1