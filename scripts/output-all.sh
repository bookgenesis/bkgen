#!/bin/bash
cd `dirname $0`; source venv
python -m bkgen.project build "$1" >output-all.log 2>&1