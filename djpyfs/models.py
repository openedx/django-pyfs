"""
Database models for django-pyfs
"""
import os

from django.db import models
from django.utils import timezone


class FSExpirations(models.Model):
    """
    Model to handle expiring temporary files.

    The modules have access to a pyfilesystem object where they can store big
    data, images, etc. In most cases, we would like those objects to expire
    (e.g. if a view generates a .PNG analytic to show to a user). This model
    keeps track of files stored, as well as the expirations of those models.
    """
    module = models.CharField(max_length=382)  # Defines the namespace
    filename = models.CharField(max_length=382)  # Filename within namespace
    expires = models.BooleanField()  # Does it expire?
    expiration = models.DateTimeField(db_index=True)  # If so, when?

    @classmethod
    def create_expiration(cls, module, filename, seconds, days=0, expires=True):
        """
        May be used instead of the constructor to create a new expiration.

        Automatically applies timedelta and saves to DB.

        Arguments:
            cls (classtype): Class this method is attached to
            module (str): Namespace of the filesystem
            filename (str): Name of the file to create the expiration for
            seconds (int): Number of seconds before we expire the file
            days (int): Number of days before we expire the file. If both days
                and seconds are given they are added together.
        """
        expiration_time = timezone.now() + timezone.timedelta(days, seconds)

        # If object exists, update it
        objects = cls.objects.filter(module=module, filename=filename)
        if objects:
            exp = objects[0]
            exp.expires = expires
            exp.expiration = expiration_time
            exp.save()
            return

        # Otherwise, create a new one
        f = cls()
        f.module = module
        f.filename = filename
        f.expires = expires
        f.expiration = expiration_time
        f.save()

    @classmethod
    def expired(cls):
        """
        Returns a list of expired objects
        """

        expiration_lte = timezone.now()
        return cls.objects.filter(expires=True, expiration__lte=expiration_lte)

    class Meta:
        app_label = 'djpyfs'
        unique_together = (("module", "filename"),)
        # We'd like to create an index first on expiration than on expires (so
        # we can search for objects where expires=True and expiration is before
        # now).
        index_together = [
            ["expiration", "expires"],
        ]

    def __str__(self):
        if self.expires:
            return "{} Expires {}".format(os.path.join(self.module, self.filename), str(self.expiration))
        else:
            return "{} Permanent ({})".format(os.path.join(self.module, self.filename), str(self.expiration))
