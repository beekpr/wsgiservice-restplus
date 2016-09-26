#!/usr/bin/env python
# -*- coding: utf-8 -*-
# flake8: noqa
from __future__ import unicode_literals

import re
import sys

from setuptools import setup, find_packages

RE_REQUIREMENT = re.compile(r'^\s*-r\s*(?P<filename>.*)$')


exec(compile(open('wsgiservice_restplus/__about__.py').read(), 'wsgiservice_restplus/__about__.py', 'exec'))

tests_require = ['nose', 'rednose', 'blinker', 'tzlocal']
install_requires = ['six>=1.3.0', 'jsonschema', 'pytz', 'aniso8601>=0.82']
doc_require = ['sphinx', 'alabaster', 'sphinx_issues']
dev_requires = ['flake8', 'minibench', 'tox', 'invoke'] + tests_require + doc_require


if sys.version_info[0:2] < (2, 7):
    install_requires += ['ordereddict']
    tests_require += ['unittest2']

try:
    from unittest.mock import Mock
except:
    tests_require += ['mock']

setup(
    name='flask-restplus',
    version=__version__,
    description=__description__,
    long_description=long_description,
    author='Axel Haustant',
    author_email='axel@data.gouv.fr',
    packages=find_packages(exclude=['tests', 'tests.*']),
    include_package_data=True,
    install_requires=install_requires,
    tests_require=tests_require,
    extras_require={
        'test': tests_require,
        'doc': doc_require,
        'dev': dev_requires,
    },
    license='MIT',
    use_2to3=True,
    zip_safe=False,
    keywords='',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python',
        'Environment :: Web Environment',
        'Operating System :: OS Independent',
        'Intended Audience :: Developers',
        'Topic :: System :: Software Distribution',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: MIT License',
    ],
)
