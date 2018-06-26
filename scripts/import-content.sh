#!/bin/bash
cd `dirname $0`; source venv
python -m bkgen.project import "$1" >import-content.log 2>&1 