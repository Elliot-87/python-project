# registry/forms.py
from django import forms
from .models import RegistryEntry
from django.contrib import admin




class RegistryForm(forms.ModelForm):
    class Meta:
        model = RegistryEntry
        exclude = ['signature_data', 'signature_image', 'created_at']
        fields = '__all__'
        