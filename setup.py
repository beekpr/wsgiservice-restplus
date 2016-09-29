#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import sys
from setuptools import setup, find_packages

from __about__ import __version__
from __about__ import __description__
from __about__ import long_description

with open('requirements.txt', 'r') as handle:
    install_requires = [ m.rstrip('\n') for m in list(handle) ]

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
    tests_require=tests_require,
    extras_require={
        'test': tests_require,
        'dev': dev_requires,
    },
    zip_safe=False,
)
