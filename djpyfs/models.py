import django
from django.db import models
import datetime

from django.utils import timezone

## Create your models here.
#class StudentBookAccesses(models.Model):
#    username = models.CharField(max_length=500, unique=True) # TODO: Should not have max_length
#    count = models.IntegerField()

class FSExpirations(models.Model):
    ''' The modules have access to a pyfilesystem object where they
    can store big data, images, etc. In most cases, we would like
    those objects to expire (e.g. if a view generates a .PNG analytic
    to show to a user). This model keeps track of files stored, as
    well as the expirations of those models. 
    '''

    @classmethod
    def create_expiration(cls, module, filename, seconds, days=0, expires = True):
        ''' May be used instead of the constructor to create a new expiration. 
        Automatically applies timedelta and saves to DB. 
        '''
        expiration_time = timezone.now() + timezone.timedelta(days, seconds)

        # If object exists, update it
        objects = cls.objects.filter(module = module, filename = filename)
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

    
    module = models.CharField(max_length=382)  # Defines the namespace
    filename = models.CharField(max_length=382)  # Filename within the namespace
    expires = models.BooleanField() # Does it expire? 
    expiration = models.DateTimeField(db_index = True) 

    @classmethod
    def expired(cls):
        ''' Returns a list of expired objects '''

        expiration_lte = timezone.now()
        return cls.objects.filter(expires=True, expiration__lte = expiration_lte)

    class Meta:
        app_label = 'djpyfs'
        unique_together = (("module","filename"))
        # We'd like to create an index first on expiration than on expires (so we can
        # search for objects where expires=True and expiration is before now).
        index_together = [
            ["expiration", "expires"],
            ]

    def __str__(self):
        if self.expires: 
            return self.module+'/'+self.filename+" Expires "+str(self.expiration)
        else:
            return self.module+'/'+self.filename+" Permanent ("+str(self.expiration)+")"
