import os, shutil
from setuptools import setup, find_packages

config = {
    "name": "bkgen",
    "version": "0.15.0",
    "description": "Core functionality for bookgenesis",
    "url": "https://github.com/bookgenesis/bkgen",
    "author": "Sean Harrison",
    "author_email": "sah@blackearth.us",
    "license": "All rights reserved.",
    "classifiers": [
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3"
    ],
    "entry_points": {},
    "install_requires": [
        "bl @ git+https://github.com/BlackEarth/bl.git@40e61c905cdec2b3539cfd38ced8df76367ea2d6#egg=bl",
        "bf @ git+https://github.com/BlackEarth/bf.git@07746346a214f75c9857d279c0f9e5ebab92741c#egg=bf",
        "bxml @ git+https://github.com/BlackEarth/bxml.git@dccf47e70af0c780f28479685f67f3b543b3f3fd#egg=bxml",
        "cssselect~=1.1.0",
        "cssutils~=1.0.2",
        "libsass~=0.19.4",
        "lxml~=4.9.2",
        "Markdown~=3.1.1",
        "pycountry~=19.8.18",
        "six~=1.13.0",
        "Unum~=4.1.4",
    ],
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

PATH = os.path.dirname(os.path.abspath(__file__))
configfn = os.path.join(PATH, 'bkgen', '__config__.ini')
if not os.path.exists(configfn):
    shutil.copy(configfn + '.TEMPLATE', configfn)

setup(
    long_description="This package contains the core BookGenesis software.",
    packages=find_packages(exclude=['contrib', 'docs', 'tests*']),
    **config
)
