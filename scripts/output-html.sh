#!/bin/bash
cd `dirname $0`; source venv
python -m bkgen.project build-html "$1" >output-html.log 2>&1