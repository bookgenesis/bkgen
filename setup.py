import os
import shutil

from setuptools import find_packages, setup

config = {
    "name": "bookgen",
    "version": "0.19.0",
    "description": "Automated genesis of books and other publications",
    "url": "https://github.com/bookgenesis/bookgen",
    "author": "Sean Harrison",
    "author_email": "sah@bookgenesis.com",
    "license": "All rights reserved.",
    "classifiers": [
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
    ],
    "entry_points": {},
    "install_requires": [
        "bxml",
        "click~=8.0.4",
        "lxml~=4.9.1",
        "Markdown~=3.4.1",
        "pycountry~=22.3.5",
        "PyYAML~=6.0",
    ],
    "extras_require": {
        "dev": [
            "black~=22.8.0",
            "isort~=5.10.1",
        ],
        "test": [
            "black~=22.8.0",
            "flake8~=5.0.4",
        ],
    },
    "package_data": {"": []},
    "data_files": [],
    "scripts": [],
}

PATH = os.path.dirname(os.path.abspath(__file__))
configfn = os.path.join(PATH, "bkgen", "__config__.ini")
if not os.path.exists(configfn):
    shutil.copy(configfn + ".TEMPLATE", configfn)

setup(
    long_description="This package contains the core BookGenesis software.",
    packages=find_packages(exclude=["contrib", "docs", "tests*"]),
    **config
)
