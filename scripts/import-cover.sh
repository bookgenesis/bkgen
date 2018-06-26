#!/bin/bash
cd `dirname $0`; source venv
python -m bkgen.project import-cover "$1" >import-cover.log 2>&1