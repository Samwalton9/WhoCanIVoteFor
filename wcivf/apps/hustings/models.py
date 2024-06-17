"""
Models for Hustings
"""

import hashlib

from django.db import models
from django.db.models import TextChoices
from django.utils import timezone
from elections.models import PostElection
from model_utils.models import TimeStampedModel


class HustingQueryset(models.QuerySet):
    def future(self):
        """
        Returns QuerySet of objects in the future or today
        """
        return self.filter(starts__date__gte=timezone.now().date())

    def displayable(self):
        """
        Excludes objects in the past unless we have a postevent url for them
        """
        return self.exclude(
            starts__date__lt=timezone.now().date(),
            postevent_url="",
        )


class HustingStatus(TextChoices):
    suggested = "suggested", "Suggested"
    published = "published", "Published"
    rejected = "rejected", "Rejected"
    unpublished = "unpublished", "Unpublished"


class Husting(TimeStampedModel):
    """
    A Husting.
    """

    post_election = models.ForeignKey(PostElection, on_delete=models.CASCADE)
    title = models.CharField(max_length=250)
    url = models.URLField(max_length=800)
    starts = models.DateTimeField()
    ends = models.DateTimeField(blank=True, null=True)
    location = models.CharField(max_length=250, blank=True, default="")
    postevent_url = models.URLField(blank=True, max_length=800)
    status = models.CharField(default=False, choices=HustingStatus.choices)

    objects = HustingQueryset.as_manager()

    class Meta:
        ordering = ["-starts"]

    @property
    def in_past(self):
        return self.starts.date() < timezone.now().date()

    @property
    def uuid(self):
        """
        Build a uuid to be used when creating an iCal event for the object
        """
        s = f"{self.title}{self.starts.timestamp()}"
        return hashlib.md5(s.encode("utf-8")).hexdigest()
