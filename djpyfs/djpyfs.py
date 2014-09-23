'''

This is a thin veneer around a pyfilesystem. It adds a few bits of
functionality:

1) Django configuration. This can go to Amazon S3 or a static
filesystem.
2) The ability to get URLs for objects stored on the filesystem.
3) The ability to create objects with a limited lifetime. A 
task can garbage-collect those objects. 

'''

import json
import os
import os.path
import types

from django.conf import settings

from models import FSExpirations


if hasattr(settings, 'DJFS'):
    djfs_settings = settings.DJFS
else:
    djfs_settings = {'type' : 'osfs',
                     'directory_root' : 'django-pyfs/static/django-pyfs', 
                     'url_root' : '/static/django-pyfs'}

if djfs_settings['type'] == 'osfs':
    from fs.osfs import OSFS
elif djfs_settings['type'] == 's3fs':
    from fs.s3fs import S3FS
    from boto.s3.connection import S3Connection
    from boto.s3.key import Key
    key_id = djfs_settings.get('aws_access_key_id', None)
    key_secret = djfs_settings.get('aws_secret_access_key', None)
    s3conn = None
else: 
    raise AttributeError("Bad filesystem: "+str(djfs_settings['type']))

def get_filesystem(namespace):
    ''' Returns a pyfilesystem for static module storage. 

    The file system will have two additional properties: 
    1) get_url: A way to get a URL for a static file download
    2) expire: A way to expire files (so they are automatically destroyed)
    '''
    if djfs_settings['type'] == 'osfs':
        return get_osfs( namespace )
    elif djfs_settings['type'] == 's3fs':
        return get_s3fs( namespace )
    else:
        raise AttributeError("Bad filesystem: "+str(djfs_settings['type']))

def expire_objects():
    ''' Remove all obsolete objects from the file systems. Untested. '''
    objects = sorted(FSExpirations.expired(), key=lambda x:x.module)
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
    ''' Patch a filesystem object to add two methods: 
          get_url returns a URL for a resource stored on that filesystem. It takes two parameters: 
              filename: Which resource
              timeout: How long that resource is available for
          expire sets a timeout on how long the system should keep the resource. It takes four parameters:
              filename: Which resource
              seconds: How long we will keep it
              days: (optional) More user-friendly if a while
              expires: (optional) boolean; if set to False, we keep the resource forever. 
          Without calling this method, we provide no guarantees on how long resources will stick around. 
    ''' 
    def expire(self, filename, seconds, days=0, expires = True):
        ''' Set the lifespan of a file on the filesystem. 

        filename: Name of file
        expire: False means the file will never be removed
        seconds and days give time to expiration. 
        '''
        FSExpirations.create_expiration(namespace, filename, seconds, days=days, expires = expires)

    fs.expire = types.MethodType(expire, fs)
    fs.get_url = types.MethodType(url_method, fs)
    return fs

def get_osfs(namespace):
    ''' Helper method to get_filesystem for a file system on disk '''
    full_path = os.path.join(djfs_settings['directory_root'], namespace)
    if not os.path.exists(full_path):
        os.makedirs(full_path)
    osfs = OSFS(full_path)
    osfs = patch_fs(osfs, namespace, lambda self, filename, timeout=0:os.path.join(djfs_settings['url_root'], namespace, filename))
    return osfs

def get_s3fs(namespace):
    ''' Helper method to get_filesystem for a file system on S3 '''
    global key_id, key_secret
    fullpath = namespace
    if 'prefix' in djfs_settings: 
        fullpath = os.path.join(djfs_settings['prefix'], fullpath)
    s3fs = S3FS(djfs_settings['bucket'], fullpath, aws_access_key=key_id, aws_secret_key=key_secret)

    def get_s3_url(self, filename, timeout=60):
        global s3conn
        try: 
            if not s3conn:
                s3conn = S3Connection(aws_access_key_id=key_id, aws_secret_access_key=key_secret)
            return s3conn.generate_url(timeout, 'GET', bucket = djfs_settings['bucket'], key = os.path.join(fullpath, filename))
        except:  # Retry on error; typically, if the connection has timed out, but the broad except covers all errors.
            s3conn = S3Connection(aws_access_key_id=key_id, aws_secret_access_key=key_secret)
            return s3conn.generate_url(timeout, 'GET', bucket = djfs_settings['bucket'], key = os.path.join(fullpath, filename))

    s3fs = patch_fs(s3fs, namespace, get_s3_url)
    return s3fs

