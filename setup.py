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
    version='1.0.6',
    description='Django pyfilesystem integration',
    author='Piotr Mitros',
    author_email='pmitros@edx.org',
    packages=['djpyfs'],
    license="Apache 2.0",
    url="https://github.com/edx/django-pyfs",
    long_description=ld,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Framework :: Django",
        "Framework :: Django :: 1.8",
        "Framework :: Django :: 1.9",
        "Framework :: Django :: 1.10",
        "Framework :: Django :: 1.11",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: Apache Software License",
    ],
    install_requires=['fs', 'boto', 'six', 'django'],
)
