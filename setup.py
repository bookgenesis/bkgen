config = {
  "name": "bkgen",
  "version": "0.0.1",
  "description": "Core functionality for bookgenesis",
  "url": "https://gitlab.com/BlackEarth/bkgen",
  "author": "Sean Harrison",
  "author_email": "sah@blackearth.us",
  "license": "All rights reserved.",
  "classifiers": [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "Programming Language :: Python :: 3"
  ],
  "entry_points": {},
  "install_requires": ["bl", "bf", "bxml", "bsql"],
  "extras_require": {
    "dev": [],
    "test": []
  },
  "package_data": {
    "": []
    },
  "data_files": [],
  "scripts": []
}

import os, json
from setuptools import setup, find_packages
from codecs import open

setup(
    long_description="This package contains the core BookGenesis software.",
    packages=find_packages(exclude=['contrib', 'docs', 'tests*']),
    **config
)
