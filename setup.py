#!/usr/bin/env python

from distutils.core import setup

setup(name='django-pyfs',
      version='1.0',
      description='Django pyfilesystem integration',
      author='Piotr Mitros',
      author_email='pmitros@edx.org',
      url='http://mitros.org/p/',
      packages=['djpyfs'],
      install_requires=[
          'setuptools',
          'future',
          'boto'
      ],
     )
