#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import sys
from setuptools import setup, find_packages

from __about__ import __version__
from __about__ import __description__
from __about__ import long_description

install_requires = [
    "pytz",
    "jsonschema",
    "six>=1.3.0",
    "aniso8601>=0.82",
    "wsgiservice==0.4.5"
]

dependency_links=[
        "https://github.com/beekpr/wsgiservice/archive/0.4.5.zip#egg=wsgiservice-0.4.5"
]

tests_require = ['nose', 'rednose', 'blinker', 'tzlocal']
dev_requires = ['minibench', 'tox', 'invoke'] + tests_require


if sys.version_info[0:2] < (2, 7):
    install_requires += ['ordereddict']
    tests_require += ['unittest2']

try:
    from unittest.mock import Mock
except:
    tests_require += ['mock']

setup(
    name='wsgiservice_restplus',
    version=__version__,
    description=__description__,
    long_description=long_description,
    authors='Filip Ciesielski, Barnabás Südy',
    author_email='filip.ciesielski@beekeeper.io, barnabas@beekeeper.io',

    include_package_data=True,
    packages=find_packages(exclude=['tests', 'tests.*']),
    install_requires=install_requires,
    dependency_links=dependency_links,
    tests_require=tests_require,
    extras_require={
        'test': tests_require,
        'dev': dev_requires,
    },
    zip_safe=False,
)