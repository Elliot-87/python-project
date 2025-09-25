# registry/forms.py
from django import forms
from .models import RegistryEntry



TISH_CHOICES = [
    ('Hostel', 'Hostel'),
    ('Informal Settlement', 'Informal Settlement'),
    ('Township', 'Township'),
    ]

class RegistryEntryForm(forms.ModelForm):
    tish_area = forms.ChoiceField(
    choices=TISH_CHOICES,
    widget=forms.Select(attrs={
        'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-primary focus:border-transparent'
    })
    )


    class Meta:
        model = RegistryEntry
        fields = '__all__'  # or specify your fields

class RegistryForm(forms.ModelForm):
    signature_data = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'signature-data'}),
        label=""
    )
    
    class Meta:
        model = RegistryEntry
        fields = '__all__'
        widgets = {
            'tish_area': forms.Select(attrs={
                'class': 'form-control',
                'required': 'required'
            }),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'race': forms.Select(attrs={'class': 'form-control'}),
            'names': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter full names'
            }),
            'surname': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter surname'
            }),
            'id_no_or_dob': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ID number or Date of Birth'
            }),
            'physical_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter physical address'
            }),
            'ward_no': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ward number'
            }),
            'contact_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Contact number'
            }),
            'social_grant': forms.Select(attrs={
                'class': 'form-control',
                'id': 'social-grant-select'
            }),
            'disability': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'recovering_service_user': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'cooperative_member': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'signature_image': forms.FileInput(attrs={
                'class': 'form-control',
                'style': 'display: none;'
            }),
            'signature_data': forms.HiddenInput(attrs={
                'id': 'signature-data'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['names'].required = True
        self.fields['surname'].required = True
        self.fields['gender'].required = True
        self.fields['tish_area'].required = True
        self.fields['signature_image'].required = False
        self.fields['signature_data'].required = False
        self.fields['social_grant'].empty_label = "Select Grant Type"
        self.fields['social_grant'].required = False