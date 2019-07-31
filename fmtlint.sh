#!/bin/bash
set -e

isort -q -rc "$@"
black -q . "$@"
flake8 "$@"