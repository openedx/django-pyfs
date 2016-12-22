#!/usr/bin/env python

import os
from setuptools import setup

fname = os.path.join(os.path.dirname(__file__), "README.md")

if os.path.exists(fname):
    ld = open(fname).read()
else:
    ld = "Django pyfilesystem integration"

setup(
    name='django-pyfs',
    version='1.0.4',
    description='Django pyfilesystem integration',
    author='Piotr Mitros',
    author_email='pmitros@edx.org',
    packages=['djpyfs'],
    license = "AGPLv3",
    url = "https://github.com/edx/django-pyfs",
    long_description = ld,
    classifiers = [
        "Development Status :: 4 - Beta",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
    ],
    install_requires=['fs'],
)
