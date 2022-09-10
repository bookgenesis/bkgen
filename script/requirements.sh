#!/bin/bash
set -eu

PACKAGE=$(dirname $(dirname $0))
pip-compile $PACKAGE/req/install.txt -o $PACKAGE/requirements.txt >/dev/null 2&>1
