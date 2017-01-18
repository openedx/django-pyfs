django-pyfs
===========

A Django module which extends pyfilesystem with several methods to
make it convenient for web use. Specifically, it extends pyfilesystem
with two methods:

    fs.get_url(filename, timeout=0)

This will return a externally-usable URL to the resource. If
timeout>0, the URL may stop working after that period (in
seconds). Details are implementation-dependent. On Amazon S3, this is
a secure URL, which is only available for that period. For a static
filesystem, the URLs are unsecure and permanent. 

    fs.expire(filename, seconds, days, expires=True)

This allows us to create temporary objects. Our use-case was that we
wanted to generate visualizations to users which were .png images. The
lifetime of those images was a single web request, so we set them to
expire after a few minutes. Another use case was memoization.

Note that expired files are not automatically removed. To remove them,
call `expire_objects()`. In our system, we had a cron job do
this for a while. Celery, manual removals, etc. are all options. 

To configure a django-pyfs to use static files, set a parameter in
Django settings: 

    DJFS = {'type' : 'osfs',
                     'directory_root' : 'djpyfs/static/djpyfs', 
                     'url_root' : '/static/djpyfs'}

Here, `directory_root` is where the files go. `url_root` is the URL
base of where your web server is configured to serve them from.

To use files on S3, you need `boto` installed. Then, 

    DJFS = {'type' : 's3fs',
            'bucket' : 'my-bucket', 
            'prefix' : '/pyfs/' } 

`bucket` is your S3 bucket. `prefix` is optional, and gives a base
within that bucket.

To get your filesystem, call: 

    def get_filesystem(namespace)

Each module should pass a unique namespace. These will typically
correspond to subdirectories within the filesystem. 

The django-pyfs interface is designed as a generic (non-Django
specific) extension to pyfilesystem. However, the specific
implementation is very Django-specific. 

Good next steps would be to:

* Allow Django storages to act as a back-end for pyfilesystem
* Allow django-pyfs to act as a back-end for Django storages
* Support more types of pyfilesystems (esp. in-memory would be nice)

State: This code is tested and has worked well in a range of settings,
and is currently deployed on edx.org. However, it doesn't have test
cases and similar, so can't be considered truly production-ready. The
expiration functionality, in particular, we are not using right now.
