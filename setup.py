#!/usr/bin/env python

import os
from setuptools import setup

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='django-pyfs',
    version='1.0.3a',
    description='Django pyfilesystem integration',
    author='Piotr Mitros',
    author_email='pmitros@edx.org',
    packages=['djpyfs'],
    license = "AGPLv3",
    url = "https://github.com/edx/django-pyfs",
    long_description = read("README.md"),
    classifiers = [
        "Development Status :: 4 - Beta",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
    ],
    install_requires=['fs'],
)
