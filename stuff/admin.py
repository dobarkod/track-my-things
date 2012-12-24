from django.contrib import admin
from django.utils.translation import ugettext as _

from .models import *


class OrganizationAdmin(admin.ModelAdmin):

    def get_member_count(obj):
        return obj.members.count()
    get_member_count.short_description = _('members')

    list_display = ('__unicode__', 'admin', get_member_count)


class OwnerAdmin(admin.ModelAdmin):

    def get_owner_type(obj):
        return _('Person') if obj.is_user else _('Organization')
    get_owner_type.short_description = _('owner type')

    list_display = ('__unicode__', get_owner_type)


class ItemOwnershipInline(admin.TabularInline):
    model = Ownership
    extra = 1


class ItemPosessionInline(admin.TabularInline):
    model = Posession
    extra = 1


class ItemAdmin(admin.ModelAdmin):
    inlines = (ItemOwnershipInline, ItemPosessionInline)
    readonly_fields = ('owner', 'holder')


admin.site.register(Organization, OrganizationAdmin)
admin.site.register(Owner, OwnerAdmin)
admin.site.register(Item, ItemAdmin)
