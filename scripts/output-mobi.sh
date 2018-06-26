#!/bin/bash
cd `dirname $0`; source venv
python -m bkgen.project build-mobi "$1" >output-mobi.log 2>&1 