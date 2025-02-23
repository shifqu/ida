"""Geo admin."""

from django import forms
from django.contrib import admin

from apps.geo.models import Address


class AddressInlineForm(forms.ModelForm):
    """Represent the Address inline form."""

    class Meta:
        """Meta class.

        Adjust the widgets to hide the company and relation fields.
        """

        widgets = {
            "company": forms.HiddenInput(),
            "relation": forms.HiddenInput(),
        }


class AddressInline(admin.StackedInline):
    """Represent the Address inline to add/remove addresses."""

    model = Address
    form = AddressInlineForm
    extra = 0
