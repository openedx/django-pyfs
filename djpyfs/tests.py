"""
Database models for django-pyfs
"""


import os
import shutil
import unittest


from unittest import mock
import boto3
from django.test import TestCase
from django.utils import timezone
from moto import mock_s3
from fs.memoryfs import MemoryFS

from . import djpyfs
from .models import FSExpirations


class FSExpirationsTest(TestCase):
    """ Tests for FSExpirations"""
    def setUp(self):
        super().setUp()
        self.fs = MemoryFS()
        self.test_file_path = '/foo/bar'
        self.expires = True
        self.expire_secs = 1
        self.expire_days = 0
        self.create_time = timezone.now()
        self.module = "unittest"

    def tearDown(self):
        super().tearDown()
        self.fs.close()

    def test_create_expiration_exists(self):
        """
        Exercises FSExpirations.create_expiration() with an existing expiration
        """
        # In the first create_expiration, it does not exist. Second loop it is
        # updating the existing row.
        for _ in range(2):
            FSExpirations.create_expiration(
                self.module, self.test_file_path, self.expire_secs, self.expire_days, self.expires
            )

            self.assertEqual(FSExpirations.objects.all().count(), 1)

            fse = FSExpirations.objects.first()
            self.assertEqual(fse.module, self.module)
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

        FSExpirations.create_expiration(self.module, self.test_file_path, expire_secs, expire_days, self.expires)

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
            self.module, self.test_file_path, expire_secs, expire_days, self.expires
        )

        # Make sure there is 1 expiration pending, but nothing currently
        # expired
        self.assertEqual(FSExpirations.objects.all().count(), 1)
        self.assertEqual(len(FSExpirations.expired()), 0)

    def test_str(self):
        # First check the unexpired version of the string
        fse = FSExpirations(
            module=self.module, filename=self.test_file_path, expiration=self.create_time, expires=False
        )
        fse2 = FSExpirations(
            module=self.module, filename=self.test_file_path, expiration=self.create_time, expires=True
        )

        for f in (fse, fse2):
            # Don't really care what __str__ is, just that it returns a string
            # of some variety and doesn't error
            try:
                result = f.__str__()
                self.assertTrue(isinstance(result, str))
            except Exception as e:  # pylint: disable=broad-except
                self.fail(f"__str__ raised an exception! {e}")


class _BaseFs(TestCase):
    """Tests for BaseFs"""
    djfs_settings = None

    def setUp(self):
        super().setUp()
        if self.djfs_settings is None:
            raise unittest.SkipTest("Skipping test on base class.")

        # Monkey patch djpyfs settings to force settings to whatever the
        # inheriting class is testing
        self.orig_djpyfs_settings = djpyfs.DJFS_SETTINGS
        djpyfs.DJFS_SETTINGS = self.djfs_settings

        self.namespace = 'unitttest'
        self.secondary_namespace = 'unittest_2'
        self.test_dir_name = 'unit_test_dir'
        self.test_file_name = 'unit_test_file'
        self.secondary_test_file_name = 'unit_test_file_2'
        self.uncreated_test_file_name = 'do_not_create'

        self.relative_path_to_test_file = os.path.join(self.test_dir_name, self.test_file_name)
        self.relative_path_to_secondary_test_file = os.path.join(self.test_dir_name, self.secondary_test_file_name)
        self.relative_path_to_uncreated_test_file = os.path.join(self.test_dir_name, self.uncreated_test_file_name)

        self.full_test_path = os.path.join(djpyfs.DJFS_SETTINGS['directory_root'], self.namespace)
        self.secondary_full_test_path = os.path.join(djpyfs.DJFS_SETTINGS['directory_root'], self.secondary_namespace)

        # We test against just the beginning of the returned url since S3 will
        # have changing query params appended.
        self.expected_url_prefix = os.path.join(
            djpyfs.DJFS_SETTINGS['url_root'], self.namespace, self.relative_path_to_test_file
        )

    def tearDown(self):
        # Restore original settings
        super().tearDown()
        djpyfs.DJFS_SETTINGS = self.orig_djpyfs_settings

    def test_get_filesystem(self):
        # Testing that using the default retrieval also gives us a usable osfs
        fs = djpyfs.get_filesystem(self.namespace)
        fs.makedir(self.test_dir_name)
        fs.getinfo(self.test_dir_name)
        fs.removedir(self.test_dir_name)

    def test_expire_objects(self):
        expire_secs = 0
        expire_days = 0

        # Need to create two different namespaces with at least two files and
        # at least one file that doesn't exist to fully exercise expire_
        # objects. They all have to be part of the same run, thus this overly
        # complicated hoo-ha.
        fs1 = djpyfs.get_filesystem(self.namespace)
        fs2 = djpyfs.get_filesystem(self.secondary_namespace)

        for curr_fs in (fs1, fs2):
            curr_fs.makedir(self.test_dir_name)

            foo = 'foo'  # pylint: disable=blacklisted-name
            curr_fs.settext(self.relative_path_to_test_file, foo, 'utf-8', 'strict')
            curr_fs.settext(self.relative_path_to_secondary_test_file, foo, 'utf-8', 'strict')

            self.assertTrue(curr_fs.exists(self.relative_path_to_test_file))
            self.assertTrue(curr_fs.exists(self.relative_path_to_secondary_test_file))
            self.assertFalse(curr_fs.exists(self.relative_path_to_uncreated_test_file))

            # Create an instant expiration for all 3 files
            curr_fs.expire(self.relative_path_to_test_file, expire_secs, expire_days)
            curr_fs.expire(self.relative_path_to_secondary_test_file, expire_secs, expire_days)
            curr_fs.expire(self.relative_path_to_uncreated_test_file, expire_secs, expire_days)

        self.assertEqual(FSExpirations.objects.all().count(), 6)

        # Expire, should delete the files that exist and do nothing for the
        # one that doesn't
        djpyfs.expire_objects()

        self.assertFalse(fs1.exists(self.relative_path_to_test_file))
        self.assertFalse(fs1.exists(self.relative_path_to_secondary_test_file))
        self.assertFalse(fs1.exists(self.relative_path_to_uncreated_test_file))

        self.assertFalse(fs2.exists(self.relative_path_to_test_file))
        self.assertFalse(fs2.exists(self.relative_path_to_secondary_test_file))
        self.assertFalse(fs2.exists(self.relative_path_to_uncreated_test_file))

        self.assertEqual(FSExpirations.objects.all().count(), 0)

    def test_get_url(self):
        fs = djpyfs.get_filesystem(self.namespace)
        fs.makedir(self.test_dir_name)

        with fs.open(self.relative_path_to_test_file, 'w') as f:
            f.write('foo')

        self.assertTrue(fs.exists(self.relative_path_to_test_file))
        self.assertTrue(fs.get_url(self.relative_path_to_test_file).startswith(self.expected_url_prefix))

    def test_get_url_does_not_exist(self):
        # Current behavior is that even if a file doesn't exist you can get a
        # URL for it
        fs = djpyfs.get_filesystem(self.namespace)
        self.assertFalse(fs.exists(self.relative_path_to_test_file))
        self.assertTrue(fs.get_url(self.relative_path_to_test_file).startswith(self.expected_url_prefix))

    def test_patch_fs(self):
        """
        Simple check to make sure the filesystem is patched as expected.
        """
        fs = djpyfs.get_filesystem(self.namespace)
        self.assertTrue(callable(getattr(fs, 'expire')))   # pylint: disable=literal-used-as-attribute
        self.assertTrue(callable(getattr(fs, 'get_url')))  # pylint: disable=literal-used-as-attribute


# pylint: disable=test-inherits-tests; literal-used-as-attribute
class BadFileSystemTestInh(_BaseFs):
    """
    Test filesystem class that uses an unknown filesystem type to make sure all
    methods return consistently. Wraps all BaseFs tests to catch the exception.
    """
    djfs_settings = {
        'type': 'bogusfs',
        'directory_root': 'django-pyfs/static/django-pyfs-test',
        'url_root': '/static/django-pyfs-test'
    }

    def test_get_filesystem(self):
        with self.assertRaises(AttributeError):
            super().test_get_filesystem()

    def test_expire_objects(self):
        with self.assertRaises(AttributeError):
            super().test_expire_objects()

    def test_get_url(self):
        with self.assertRaises(AttributeError):
            super().test_get_url()

    def test_get_url_does_not_exist(self):
        with self.assertRaises(AttributeError):
            super().test_get_url_does_not_exist()

    def test_patch_fs(self):
        with self.assertRaises(AttributeError):
            super().test_patch_fs()


# pylint: disable=test-inherits-tests
class OsfsTest(_BaseFs):
    """
    Tests the OSFS implementation.
    """
    djfs_settings = {
        'type': 'osfs',
        'directory_root': 'django-pyfs/static/django-pyfs-test',
        'url_root': '/static/django-pyfs-test'
    }

    def _cleanDirs(self):
        # If anything is left from last run, try to clean it
        shutil.rmtree(self.full_test_path, ignore_errors=True)
        shutil.rmtree(self.secondary_full_test_path, ignore_errors=True)

    def setUp(self):
        super().setUp()
        self._cleanDirs()

    def tearDown(self):
        super().tearDown()
        self._cleanDirs()


# pylint: disable=test-inherits-tests
class S3Test(_BaseFs):
    """
    Tests the S3FS implementation, without a prefix.
    """
    djfs_settings = {
        'type': 's3fs',
        'directory_root': 'django-pyfs/static/django-pyfs-test',
        'url_root': '/static/django-pyfs-test',
        'aws_access_key_id': 'foo',
        'aws_secret_access_key': 'bar',
        'bucket': 'test_bucket'
    }

    def setUp(self):
        super().setUp()

        self.expected_url_prefix = "https://{}.s3.amazonaws.com:443/{}/{}".format(
            djpyfs.DJFS_SETTINGS['bucket'], self.namespace, self.relative_path_to_test_file
        )

        self._setUpS3()

    def _setUpS3(self):
        """setup class"""

        # Start mocking S3
        self.mock_s3 = mock_s3()
        self.mock_s3.start()

        # Create our fake bucket in fake s3
        self.conn = boto3.resource('s3')
        self.conn.create_bucket(Bucket=djpyfs.DJFS_SETTINGS['bucket'])

    # This test is only relevant for S3. Generate some fake errors to make
    # sure we cover the retry code.
    def test_get_url_retry(self):
        with mock.patch("boto.s3.connection.S3Connection.generate_url") as mock_exception:
            mock_exception.side_effect = AttributeError("test mock exception")
            fs = djpyfs.get_filesystem(self.namespace)

            with self.assertRaises(AttributeError):
                fs.get_url(self.relative_path_to_test_file).startswith(self.expected_url_prefix)

    def tearDown(self):
        self.mock_s3.stop()
        super().tearDown()


# pylint: disable=test-inherits-tests
class S3TestPrefix(S3Test):
    """
    Same as S3Test above, but includes a prefix.
    """

    djfs_settings = {
        'type': 's3fs',
        'directory_root': 'django-pyfs/static/django-pyfs-test',
        'url_root': '/static/django-pyfs-test',
        'aws_access_key_id': 'foo',
        'aws_secret_access_key': 'bar',
        'bucket': 'test_bucket',
        'prefix': 'prefix'
    }

    def setUp(self):
        super().setUp()

        self.expected_url_prefix = "https://{}.s3.amazonaws.com:443/{}/{}/{}".format(
            djpyfs.DJFS_SETTINGS['bucket'], djpyfs.DJFS_SETTINGS['prefix'],
            self.namespace, self.relative_path_to_test_file
        )

        self._setUpS3()
