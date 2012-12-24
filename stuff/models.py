from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.utils.translation import ugettext_lazy as _
from django.utils.timezone import now

from uuid import uuid4
import os.path


class Organization(models.Model):

    name = models.CharField(max_length=255, verbose_name=_('name'),
        help_text=_('Name of the organization'))
    admin = models.ForeignKey(User, related_name='administered_organizations')
    members = models.ManyToManyField(User, related_name='organizations')

    def __unicode__(self):
        return unicode(self.name)

    @staticmethod
    def create(*args, **kwargs):
        return Organization.objects.create(*args, **kwargs)


class Owner(models.Model):

    user = models.OneToOneField(User, blank=True, null=True)
    organization = models.OneToOneField(Organization, blank=True, null=True)

    def __unicode__(self):
        if self.is_user:
            return unicode(self.user)
        else:
            return unicode(self.organization)

    def clean(self):
        if self.user_id and self.organization_id:
            raise ValidationError("Owner can't be both user and organization")
        if not self.user_id and not self.organization_id:
            raise ValidationError("Owner must be either user or organization")

    def save(self, *args, **kwargs):
        self.clean()
        super(Owner, self).save(*args, **kwargs)

    @staticmethod
    def create_for_user(user):
        return Owner.objects.create(user=user)

    @staticmethod
    def create_for_organization(organization):
        return Owner.objects.create(organization=organization)

    @property
    def is_user(self):
        return self.user_id is not None

    @property
    def is_organization(self):
        return self.organization_id is not None

    @property
    def owned_items(self):
        return Item.objects.filter(ownership__owner=self, ownership__end=None)

    @property
    def held_items(self):
        return Item.objects.filter(posession__holder=self, posession__end=None)

    @property
    def borrowed_items(self):
        return self.held_items.exclude(
            id__in=self.owned_items.values_list('id', flat=True))

    @property
    def lent_items(self):
        return self.owned_items.exclude(
            id__in=self.held_items.values_list('id', flat=True))


class ItemManager(models.Manager):
    use_for_related_fields = True

    def create(self, owner, **kwargs):
        item = super(ItemManager, self).create(**kwargs)
        item.owner = owner
        item.holder = owner
        return item


class Item(models.Model):
    TYPES = (
        ('book', _('Book')),
        ('other', _('Other'))
    )

    @staticmethod
    def _upload_to(instance, name):
        x = uuid4().hexdigest
        fname, ext = os.path.splitext(name)
        return os.path.join(x[0:2], x[2:4], x[4:], ext)

    objects = ItemManager()

    type = models.CharField(max_length=255, choices=TYPES, default='other',
        verbose_name=_('type'), help_text=_('Type of the item'))
    name = models.CharField(max_length=255, verbose_name=_('name'),
        help_text=_('Item name'))
    description = models.TextField(blank=True, verbose_name=_('description'),
        help_text=_('Description of the item'))
    image = models.ImageField(upload_to=_upload_to, blank=True, null=True)
    value = models.DecimalField(decimal_places=2, max_digits=11, default=0)
    disposed = models.BooleanField(default=False)

    created = models.DateTimeField(auto_now_add=True, editable=False)
    updated = models.DateTimeField(auto_now=True, editable=False)

    @staticmethod
    def create(*args, **kwargs):
        return Item.objects.create(*args, **kwargs)

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.clean()
        super(Item, self).save(*args, **kwargs)

    def clean(self):
        if self.type not in dict(self.TYPES):
            raise ValidationError(_('Unknown item type %s') % self.type)

    @property
    def owner(self):
        ownership = self.ownership_set.get_current_for_item(self)
        return ownership.owner if ownership else None

    @owner.setter
    def owner(self, owner):
        ownership = self.ownership_set.get_current_for_item(self)
        if ownership and ownership.owner == owner:
            return
        elif ownership:
            ownership.end = now()
            ownership.save()

        Ownership.objects.create(item=self, owner=owner)

    @owner.deleter
    def owner(self):
        ownership = self.ownership_set.get_current_for_item(self)
        if ownership:
            ownership.end = now()
            ownership.save()

    @property
    def holder(self):
        posession = self.posession_set.get_current_for_item(self)
        return posession.holder if posession else None

    @holder.setter
    def holder(self, holder):
        posession = self.posession_set.get_current_for_item(self)
        if posession and posession.holder == holder:
            return
        elif posession:
            posession.end = now()
            posession.save()

        Posession.objects.create(item=self, holder=holder)

    @holder.deleter
    def holder(self):
        posession = self.posession_set.get_current_for_item(self)
        if posession:
            posession.end = now()
            posession.save()

    def return_to_owner(self):
        self.holder = self.owner

    def dispose(self):
        del self.holder
        del self.owner
        self.disposed = True
        self.save()


class TemporaryItemLinkManager(models.Manager):
    use_for_related_fields = True

    def get_current_for_item(self, item):
        try:
            return self.get(item=item, end=None)
        except ObjectDoesNotExist:
            return None


class TemporaryItemLink(models.Model):

    item = models.ForeignKey(Item)
    start = models.DateTimeField(default=now)
    end = models.DateTimeField(blank=True, null=True)

    objects = TemporaryItemLinkManager()

    class Meta:
        abstract = True

    def __unicode__(self):
        return u'%s @ %s [%s - %s]' % (
            unicode(self.item),
            unicode(self.owner) \
                if hasattr(self, 'owner') else unicode(self.holder),
            self.start.strftime('%Y-%m-%d %H:%M'),
            self.end.strftime('%Y-%m-%d %H:%M') if self.end else '')


class Posession(TemporaryItemLink):
    holder = models.ForeignKey(Owner)


class Ownership(TemporaryItemLink):
    owner = models.ForeignKey(Owner)
