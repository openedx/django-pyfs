"""
This is a thin veneer around a `pyfilesystem`. It adds a few bits of
functionality:

1) Django configuration. This can go to Amazon S3 or a static
filesystem.
2) The ability to get URLs for objects stored on the filesystem.
3) The ability to create objects with a limited lifetime. A
task can garbage-collect those objects.
"""

import os
import os.path
import types

from boto.s3.connection import S3Connection
from django.conf import settings
from fs.osfs import OSFS
from fs_s3fs import S3FS
from .models import FSExpirations

if hasattr(settings, 'DJFS'):
    DJFS_SETTINGS = settings.DJFS  # pragma: no cover
else:
    DJFS_SETTINGS = {'type': 'osfs',
                     'directory_root': 'django-pyfs/static/django-pyfs',
                     'url_root': '/static/django-pyfs'}

# Global to hold the active S3 connection. Prevents needing to reconnect
# several times in a request. Connections are set up below in `get_s3_url`.
S3CONN = None


def get_filesystem(namespace):
    """
    Returns a patched pyfilesystem for static module storage based on
    `DJFS_SETTINGS`. See `patch_fs` documentation for additional details.

    The file system will have two additional properties:
      1) get_url: A way to get a URL for a static file download
      2) expire: A way to expire files (so they are automatically destroyed)
    """
    if DJFS_SETTINGS['type'] == 'osfs':
        return get_osfs(namespace)
    elif DJFS_SETTINGS['type'] == 's3fs':
        return get_s3fs(namespace)
    else:
        raise AttributeError("Bad filesystem: " + str(DJFS_SETTINGS['type']))


def expire_objects():
    """
    Remove all obsolete objects from the file systems.
    """
    objects = sorted(FSExpirations.expired(), key=lambda x: x.module)
    fs = None
    module = None
    for o in objects:
        if module != o.module:
            module = o.module
            fs = get_filesystem(module)
        if fs.exists(o.filename):
            fs.remove(o.filename)
        o.delete()


def patch_fs(fs, namespace, url_method):
    """
    Patch a filesystem instance to add the `get_url` and `expire` methods.

    Arguments:
        fs (obj): The pyfilesystem subclass instance to be patched.
        namespace (str): Namespace of the filesystem, used in `expire`
        url_method (func): Function to patch into the filesyste instance as
            `get_url`. Allows filesystem independent implementation.
    Returns:
        obj: Patched filesystem instance
    """

    def expire(self, filename, seconds, days=0, expires=True):  # pylint: disable=unused-argument
        """
        Set the lifespan of a file on the filesystem.

        Arguments:
            filename (str): Name of file
            expires (bool): False means the file will never be removed seconds
                and days give time to expiration.
            seconds (int): (optional) how many seconds to keep the file around
            days (int): (optional) how many days to keep the file around for.
                If both days and seconds are given they will be added
                together. So `seconds=86400, days=1` would expire the file
                in 2 days.

        Returns:
            None
        """
        FSExpirations.create_expiration(namespace, filename, seconds, days=days, expires=expires)

    fs.expire = types.MethodType(expire, fs)
    fs.get_url = types.MethodType(url_method, fs)
    return fs


def get_osfs(namespace):
    """
    Helper method to get_filesystem for a file system on disk
    """
    full_path = os.path.join(DJFS_SETTINGS['directory_root'], namespace)
    if not os.path.exists(full_path):
        os.makedirs(full_path)
    osfs = OSFS(full_path)
    osfs = patch_fs(
        osfs,
        namespace,
        # This is the OSFS implementation of `get_url`, note that it ignores
        # the timeout param so all OSFS file urls have no time limits.
        lambda self, filename, timeout=0: os.path.join(DJFS_SETTINGS['url_root'], namespace, filename)
    )
    return osfs


def get_s3fs(namespace):
    """
    Helper method to get_filesystem for a file system on S3
    """
    key_id = DJFS_SETTINGS.get('aws_access_key_id', None)
    key_secret = DJFS_SETTINGS.get('aws_secret_access_key', None)

    fullpath = namespace

    if 'prefix' in DJFS_SETTINGS:
        fullpath = os.path.join(DJFS_SETTINGS['prefix'], fullpath)
    s3fs = S3FS(DJFS_SETTINGS['bucket'], fullpath, aws_secret_access_key=key_id, aws_access_key_id=key_secret)

    def get_s3_url(self, filename, timeout=60):  # pylint: disable=unused-argument
        """
        Patch method to returns a signed S3 url for the given filename

        Note that this will return a url whether or not the requested file
        exsits.

        Arguments:
            self (obj): S3FS instance that this function has been patched onto
            filename (str): The name of the file we are retrieving a url for
            timeout (int): How long the url should be valid for; S3 enforces
                this limit

        Returns:
            str: A signed url to the requested file in S3
        """
        global S3CONN

        try:
            if not S3CONN:
                S3CONN = S3Connection(aws_access_key_id=key_id, aws_secret_access_key=key_secret)
            return S3CONN.generate_url(
                timeout, 'GET', bucket=DJFS_SETTINGS['bucket'], key=os.path.join(fullpath, filename)
            )
        except Exception:  # pylint: disable=broad-except
            # Retry on error; typically, if the connection has timed out, but
            # the broad except covers all errors.
            S3CONN = S3Connection(aws_access_key_id=key_id, aws_secret_access_key=key_secret)

            return S3CONN.generate_url(
                timeout, 'GET', bucket=DJFS_SETTINGS['bucket'], key=os.path.join(fullpath, filename)
            )

    s3fs = patch_fs(s3fs, namespace, get_s3_url)
    return s3fs
