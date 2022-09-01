import os
import shutil

from setuptools import find_packages, setup

config = {
    "name": "bkgen",
    "version": "0.19.0",
    "description": "Core functionality for bookgenesis",
    "url": "https://gitlab.com/bookgenesis/bkgen",
    "author": "Sean Harrison",
    "author_email": "sah@bookgenesis.com",
    "license": "All rights reserved.",
    "classifiers": [
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
    ],
    "entry_points": {},
    "install_requires": ["bl", "bf", "bxml", "pycountry"],
    "extras_require": {"dev": [], "test": []},
    "package_data": {"": []},
    "data_files": [],
    "scripts": [],
}

PATH = os.path.dirname(os.path.abspath(__file__))
configfn = os.path.join(PATH, 'bkgen', '__config__.ini')
if not os.path.exists(configfn):
    shutil.copy(configfn + '.TEMPLATE', configfn)

setup(
    long_description="This package contains the core BookGenesis software.",
    packages=find_packages(exclude=['contrib', 'docs', 'tests*']),
    **config
)
