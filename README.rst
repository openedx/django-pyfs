openedx-django-pyfs
===================

|pypi-badge| |ci-badge| |codecov-badge| |pyversions-badge|
|license-badge|

A Django module which extends pyfilesystem2 with several methods to
make it convenient for web use. Specifically, it extends pyfilesystem2
with two methods:

.. code-block::

    fs.get_url(filename, timeout=0)

This will return a externally-usable URL to the resource. If
timeout>0, the URL may stop working after that period (in
seconds). Details are implementation-dependent. On Amazon S3, this is
a secure URL, which is only available for that period. For a static
filesystem, the URLs are unsecure and permanent.

.. code-block::

    fs.expire(filename, seconds, days, expires=True)

This allows us to create temporary objects. Our use-case was that we
wanted to generate visualizations to users which were .png images. The
lifetime of those images was a single web request, so we set them to
expire after a few minutes. Another use case was memoization.

Note that expired files are not automatically removed. To remove them,
call ``expire_objects()``. In our system, we had a cron job do
this for a while. Celery, manual removals, etc. are all options.

To configure a openedx-django-pyfs to use static files, set a parameter in
Django settings:

.. code-block::

    DJFS = {'type' : 'osfs',
            'directory_root' : 'djpyfs/static/djpyfs',
            'url_root' : '/static/djpyfs'}

Here, ``directory_root`` is where the files go. ``url_root`` is the URL
base of where your web server is configured to serve them from.

To use files on S3, you need ``boto`` installed. Then,

.. code-block::

    DJFS = {'type' : 's3fs',
            'bucket' : 'my-bucket',
            'prefix' : '/pyfs/' }

``bucket`` is your S3 bucket. ``prefix`` is optional, and gives a base
within that bucket.

To get your filesystem, call:

.. code-block::

    def get_filesystem(namespace)

Each module should pass a unique namespace. These will typically
correspond to subdirectories within the filesystem.

The openedx-django-pyfs interface is designed as a generic (non-Django
specific) extension to pyfilesystem2. However, the specific
implementation is very Django-specific.

Good next steps would be to:

* Allow Django storages to act as a back-end for pyfilesystem
* Allow openedx-django-pyfs to act as a back-end for Django storages
* Support more types of pyfilesystems (esp. in-memory would be nice)

State: This code is tested and has worked well in a range of settings,
and is currently deployed on edx.org.

.. |pypi-badge| image:: https://img.shields.io/pypi/v/openedx-django-pyfs.svg
    :target: https://pypi.python.org/pypi/openedx-django-pyfs/
    :alt: PyPI

.. |ci-badge| image:: https://github.com/openedx/django-pyfs/workflows/Python%20CI/badge.svg?branch=master
    :target: https://github.com/openedx/django-pyfs/actions?query=workflow%3A%22Python+CI%22
    :alt: Github CI

.. |codecov-badge| image:: http://codecov.io/github/openedx/django-pyfs/coverage.svg?branch=master
    :target: http://codecov.io/github/openedx/django-pyfs?branch=master
    :alt: Codecov

.. |pyversions-badge| image:: https://img.shields.io/pypi/pyversions/openedx-django-pyfs.svg
    :target: https://pypi.python.org/pypi/openedx-django-pyfs
    :alt: Supported Python versions

.. |license-badge| image:: https://img.shields.io/github/license/openedx/django-pyfs.svg
    :target: https://github.com/openedx/django-pyfs/blob/master/LICENSE.txt
    :alt: License
