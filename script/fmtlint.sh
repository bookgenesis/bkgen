#!/bin/bash
set -eu

PACKAGE=$(dirname $(dirname $0))
LOCATION=${1:-$PACKAGE/bkgen}

isort --profile black $LOCATION
black $LOCATION
flake8 $LOCATION
