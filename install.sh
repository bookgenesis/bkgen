#!/bin/bash

# change to the script directory and calculate needed variables
cd `dirname $0`
PACKAGE_PATH=`pwd`
PACKAGE_NAME=`basename $PACKAGE_PATH`
VENV=`dirname $PACKAGE_PATH`/.venv/$PACKAGE_NAME	# virtualenv location as hidden subfolder
PYTHON=$VENV/bin/python 			# the virtualenv's python interpreter
PACKAGE_PARAMS=$1					# any package config parameters can be passed via $1: JSON object string

# create a python virtual environment for this package
echo "creating virtual environment in $VENV"
python3 -m virtualenv $VENV
SYMLINK=$PACKAGE_PATH/venv 			# so you can type "source venv" in the package directory
rm -f $SYMLINK
ln -s $VENV/bin/activate $SYMLINK

# install this package and its dependencies in the virtual environment
$PYTHON -m pip -q install -r $PACKAGE_PATH/requirements.txt
$PYTHON -m pip -q install -e $PACKAGE_PATH

echo "Installation complete. 
You can activate this package's virtualenv at the command prompt by typing
	$ source `basename $SYMLINK`
in the package directory."

