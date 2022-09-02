#!/bin/bash
set -eu

PACKAGE=$(dirname $(dirname $0))
isort --profile black $PACKAGE
black $PACKAGE
flake8 $PACKAGE
