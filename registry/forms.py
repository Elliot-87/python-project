# registry/forms.py
from django import forms
from .models import RegistryEntry

class RegistryForm(forms.ModelForm):
    class Meta:
        model = RegistryEntry
        fields = [
            'names',
            'surname',
            'id_no_or_dob',   # <-- use this (matches models.py)
            'gender',
            'disability',
            'physical_address',
            'tish_area',
            'ward_no',
            'contact_number',
            'race',
            'recovering_service_user',
            'social_grant',
            'cooperative_member',
            'sign',
        ]
