#!/usr/bin/env python

import os
import re
from setuptools import setup

fname = os.path.join(os.path.dirname(__file__), "README.rst")

if os.path.exists(fname):
    ld = open(fname).read()
else:
    ld = "Django pyfilesystem integration"


def is_requirement(line):
    """
    Return True if the requirement line is a package requirement;
    that is, it is not blank, a comment, or editable.
    """
    # Remove whitespace at the start/end of the line
    line = line.strip()

    # Skip blank lines, comments, and editable installs
    return not (
        line == '' or
        line.startswith('-r') or
        line.startswith('#') or
        line.startswith('-e') or
        line.startswith('git+') or
        line.startswith('-c')
    )


def load_requirements(*requirements_paths):
    """
    Load all requirements from the specified requirements files.
    Returns a list of requirement strings.
    """
    requirements = set()
    for path in requirements_paths:
        requirements.update(
            line.split('#')[0].strip() for line in open(path).readlines()
            if is_requirement(line)
        )
    return list(requirements)


def get_version(*file_paths):
    """
    Extract the version string from the file at the given relative path fragments.
    """
    filename = os.path.join(os.path.dirname(__file__), *file_paths)
    with open(filename, encoding='utf-8') as opened_file:
        version_file = opened_file.read()
        version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                                  version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError('Unable to find version string.')


VERSION = get_version("djpyfs", "__init__.py")


setup(
    name='django-pyfs',
    version=VERSION,
    description='Django pyfilesystem integration',
    author='Piotr Mitros',
    author_email='pmitros@edx.org',
    packages=['djpyfs'],
    license="Apache 2.0",
    url="https://github.com/edx/django-pyfs",
    long_description=ld,
    long_description_content_type='text/x-rst',
    classifiers=[
        "Development Status :: 4 - Beta",
        "Framework :: Django",
        'Framework :: Django :: 2.2',
        'Framework :: Django :: 3.0',
        'Framework :: Django :: 3.1',
        'Framework :: Django :: 3.2',
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: Apache Software License",
    ],
    install_requires=load_requirements('requirements/base.in'),
    tests_require=load_requirements('requirements/test.in'),
)
