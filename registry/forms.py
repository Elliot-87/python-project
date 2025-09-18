# registry/forms.py
from django import forms
from .models import RegistryEntry
from django.contrib import admin




class RegistryForm(forms.ModelForm):
    class Meta:
        model = RegistryEntry
        exclude = ['signature_data', 'signature_image', 'created_at']
        fields = '__all__'
        
        exclude = ['signature_data', 'signature_image']
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
            
        ]
