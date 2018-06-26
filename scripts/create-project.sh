#!/bin/bash
cd `dirname $0`; source venv
python -m bkgen.project create "$1" >create-project.log 2>&1