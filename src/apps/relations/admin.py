"""Relations admin."""

from django.contrib import admin

from apps.geo.admin import AddressInline
from apps.relations.models import Relation


class RelationAdmin(admin.ModelAdmin):
    """Represent the Relation admin."""

    inlines = [AddressInline]
    list_filter = ("category",)


admin.site.register(Relation, RelationAdmin)
