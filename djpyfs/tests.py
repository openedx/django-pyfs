from __future__ import absolute_import, unicode_literals
from future.builtins import range

import shutil
import os
import sys
import unittest

import boto
from django.test import TestCase
from django.utils import timezone
from fs.memoryfs import MemoryFS
from moto import mock_s3

from . import djpyfs
from .models import FSExpirations


class FSExpirationsTest(TestCase):
    def setUp(self):
        self.fs = MemoryFS()
        self.test_file_path = '/foo/bar'
        self.expires = True
        self.expire_secs = 1
        self.expire_days = 0
        self.create_time = timezone.now()

    def tearDown(self):
        self.fs.close()

    def test_create_expiration_exists(self):
        """
        Exercises FSExpirations.create_expiration() with an existing expiration
        """
        # In the first create_expiration, it does not exist. Second loop it is updating the existing row.
        for _ in range(2):
            FSExpirations.create_expiration(
                self.fs, self.test_file_path, self.expire_secs, self.expire_days, self.expires
            )

            self.assertEqual(FSExpirations.objects.all().count(), 1)

            fse = FSExpirations.objects.first()
            self.assertEqual(fse.module, self.fs.__str__())
            self.assertEqual(fse.filename, self.test_file_path)
            self.assertEqual(fse.expires, self.expires)

            # Check expiration time within a couple of seconds
            self.assertGreaterEqual(fse.expiration, self.create_time)
            self.assertLessEqual(fse.expiration, self.create_time + timezone.timedelta(seconds=self.expire_secs + 3))

    def test_expired(self):
        """
        Exercises FSExpirations.expired() with an expired expiration
        """
        expire_secs = 0
        expire_days = 0

        FSExpirations.create_expiration(
            self.fs, self.test_file_path, expire_secs, expire_days, self.expires
        )

        self.assertEqual(FSExpirations.objects.all().count(), 1)
        fse = FSExpirations.objects.first()

        self.assertEqual(fse.expires, True)

        expirations = fse.expired()
        self.assertEqual(len(expirations), 1)
        self.assertEqual(expirations[0], fse)

    def test_expired_is_not_expired(self):
        """
        Exercises FSExpirations.expired() with no expired expirations
        """
        # Make sure an empty result is empty, not an exception
        self.assertEqual(len(FSExpirations.expired()), 0)

        # Create a future expiration
        expire_secs = 30
        expire_days = 0
        FSExpirations.create_expiration(
            self.fs, self.test_file_path, expire_secs, expire_days, self.expires
        )

        # Make sure there is 1 expiration pending, but nothing currently expired
        self.assertEqual(FSExpirations.objects.all().count(), 1)
        self.assertEqual(len(FSExpirations.expired()), 0)


class OsfsTest(TestCase):
    def setUp(self):
        # Monkey patch djpyfs settings to force osfs. Should really be a mock.patch, but I couldn't get it to work.
        self.orig_djpyfs_settings = djpyfs.djfs_settings
        djpyfs.djfs_settings = {
            'type': 'osfs',
            'directory_root': 'django-pyfs/static/django-pyfs-test',
            'url_root': '/static/django-pyfs-test'
        }

        self.namespace = 'unitttest'
        self.test_dir_name = 'unit_test_dir'
        self.test_file_name = 'unit_test_file'
        self.relative_path_to_test_file = os.path.join(self.test_dir_name, self.test_file_name)
        self.full_test_path = os.path.join(djpyfs.djfs_settings['directory_root'], self.namespace)

        # If anything is left from last run, try to clean it
        shutil.rmtree(self.full_test_path, ignore_errors=True)

    def tearDown(self):
        # Restore original settings
        djpyfs.djfs_settings = self.orig_djpyfs_settings

        # Clean up temp files
        shutil.rmtree(self.full_test_path, ignore_errors=True)

    def test_osfs_get_osfs(self):
        """
        Exercises getting the fs by type directly by checking that we get a usable fs back.
        """
        fs = djpyfs.get_osfs(self.namespace)
        fs.makedir(self.test_dir_name)
        fs.getinfo(self.test_dir_name)
        fs.removedir(self.test_dir_name)

    def test_get_filesystem(self):
        """
        Exercises getting the fs by generic interface by checking that we get a usable fs back.
        """
        # Testing that using the default retrieval also gives us a usable osfs
        fs = djpyfs.get_filesystem(self.namespace)
        fs.makedir(self.test_dir_name)
        fs.getinfo(self.test_dir_name)
        fs.removedir(self.test_dir_name)

    @unittest.skip("Does not currently work, looks like an issue with namespacing.")
    def test_expire_objects(self):
        """
        Exercises filesystem expirations
        """
        fs = djpyfs.get_filesystem(self.namespace)
        fs.makedir(self.test_dir_name)

        self.assertEqual(fs.create(self.relative_path_to_test_file), True)

        # Create an instant expiration
        expire_secs = 0
        expire_days = 0
        FSExpirations.create_expiration(fs, self.relative_path_to_test_file, expire_secs, expire_days, True)

        # Expire, should delete the file
        djpyfs.expire_objects()

        self.assertEqual(fs.exists(self.relative_path_to_test_file), False)
        self.assertEqual(FSExpirations.objects.all().count(), 0)

    def test_get_url(self):
        fs = djpyfs.get_filesystem(self.namespace)
        fs.makedir(self.test_dir_name)

        with fs.open(self.relative_path_to_test_file, 'w') as f:
            f.write('foo')

        expected_url = os.path.join(djpyfs.djfs_settings['url_root'], self.namespace, self.relative_path_to_test_file)
        self.assertEqual(fs.get_url(self.relative_path_to_test_file), expected_url)

    def test_patch_fs(self):
        """
        Simple check to make sure the filesystem is getting patched as expected.
        """
        fs = djpyfs.get_filesystem(self.namespace)
        self.assertTrue(callable(getattr(fs, 'expire')))
        self.assertTrue(callable(getattr(fs, 'get_url')))


class S3Test(TestCase):
    @mock_s3
    def setUp(self):
        # Monkey patch djpyfs settings to force s3fs. Should really be a mock.patch, but I couldn't get it to work.
        self.orig_djpyfs_settings = djpyfs.djfs_settings
        djpyfs.djfs_settings = {
            'type': 's3fs',
            'directory_root': 'django-pyfs/static/django-pyfs-test',
            'url_root': '/static/django-pyfs-test',
            'aws_access_key_id': 'foo',
            'aws_secret_access_key': 'bar',
            'bucket': 'test_bucket'
        }

        self.namespace = 'unitttest'
        self.test_dir_name = 'unit_test_dir'
        self.test_file_name = 'unit_test_file'
        self.relative_path_to_test_file = os.path.join(self.test_dir_name, self.test_file_name)
        self.full_test_path = os.path.join(djpyfs.djfs_settings['directory_root'], self.namespace)

    def tearDown(self):
        # Restore original settings
        djpyfs.djfs_settings = self.orig_djpyfs_settings

    def _setupS3(self):
        # Create our fake bucket in fake s3
        self.conn = boto.connect_s3()
        self.conn.create_bucket(djpyfs.djfs_settings['bucket'])

    @mock_s3
    def test_osfs_get_osfs(self):
        self._setupS3()

        # Testing that we get back a usable osfs
        fs = djpyfs.get_s3fs(self.namespace)
        fs.makedir(self.test_dir_name)
        fs.getinfo(self.test_dir_name)
        fs.removedir(self.test_dir_name)

    @mock_s3
    def test_get_filesystem(self):
        self._setupS3()

        # Testing that using the default retrieval also gives us a usable osfs
        fs = djpyfs.get_filesystem(self.namespace)
        fs.makedir(self.test_dir_name)
        fs.getinfo(self.test_dir_name)
        fs.removedir(self.test_dir_name)

    @unittest.skip("Does not currently work, looks like an issue with namespacing.")
    def test_expire_objects(self):
        self._setupS3()

        fs = djpyfs.get_filesystem(self.namespace)
        fs.makedir(self.test_dir_name)

        # Create our test file
        self.assertEqual(fs.create(self.relative_path_to_test_file), True)

        # Create an instant expiration
        expire_secs = 0
        expire_days = 0
        FSExpirations.create_expiration(fs, self.relative_path_to_test_file, expire_secs, expire_days, True)

        # Expire, should delete the file
        djpyfs.expire_objects()

        self.assertEqual(fs.exists(self.relative_path_to_test_file), False)
        self.assertEqual(FSExpirations.objects.all().count(), 0)

    @mock_s3
    def test_get_url(self):
        self._setupS3()

        fs = djpyfs.get_filesystem(self.namespace)
        fs.makedir(self.test_dir_name)

        with fs.open(self.relative_path_to_test_file, 'w') as f:
            f.write('foo')

        # For some reason the Py3 version of get_url returns a port in this test, while the Py2 version does not.
        if sys.version_info[0] == 2:
            expected_url_prefix = "https://{}.s3.amazonaws.com/{}/{}".format(
                djpyfs.djfs_settings['bucket'], self.namespace, self.relative_path_to_test_file
            )
        else:
            expected_url_prefix = "https://{}.s3.amazonaws.com:443/{}/{}".format(
                djpyfs.djfs_settings['bucket'], self.namespace, self.relative_path_to_test_file
            )

        self.assertTrue(fs.get_url(self.relative_path_to_test_file).startswith(expected_url_prefix))

    @mock_s3
    def test_patch_fs(self):
        self._setupS3()

        fs = djpyfs.get_filesystem(self.namespace)
        self.assertTrue(callable(getattr(fs, 'expire')))
        self.assertTrue(callable(getattr(fs, 'get_url')))
