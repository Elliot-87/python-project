# registry/models.py
from django.db import models

class RegistryEntry(models.Model):
    # Define choices FIRST, before using them in fields
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]
    
    RACE_CHOICES = [
        ('Black', 'Black'),
        ('White', 'White'),
        ('Colored', 'Colored'),
        ('Indian', 'Indian'),
        ('Other', 'Other'),
    ]
    
    TISH_CHOICES = [
        ('', 'Select Area Type'),
        ('Hostel', 'Hostel'),
        ('Township', 'Township'), 
        ('Informal Settlement', 'Informal Settlement'),
    ]
    
    SOCIAL_GRANT_CHOICES = [
        ('None', 'No Social Grant'),
        ('CSG', 'Child Support Grant'),
        ('SRD', 'Social Relief Distress'),
        ('Older Persons', 'Older Persons Grant'),
        ('Disability', 'Disability Grant'),
        ('Foster Care', 'Foster Care Grant'),
        ('Other', 'Other Grant'),
    ]

    # Personal Information
    names = models.CharField(max_length=100)
    surname = models.CharField(max_length=100)
    id_no_or_dob = models.CharField(max_length=50, verbose_name="ID Number or Date of Birth")
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    
    # Residence Information
    physical_address = models.TextField(blank=True)
    tish_area = models.CharField(
        max_length=50, 
        choices=TISH_CHOICES,
        blank=True,
        verbose_name="TISH Area"
    )
    ward_no = models.CharField(max_length=20, blank=True, verbose_name="Ward Number")
    
    # Contact & Demographics
    contact_number = models.CharField(max_length=20, blank=True)
    race = models.CharField(max_length=20, choices=RACE_CHOICES, blank=True)
    
    # Status Information
    disability = models.BooleanField(default=False)
    recovering_service_user = models.BooleanField(default=False, verbose_name="Recovering Service User")
    social_grant = models.CharField(
        max_length=50,
        choices=SOCIAL_GRANT_CHOICES,
        default='None',
        blank=True,
        verbose_name="Social Grant Type"
    )
    cooperative_member = models.BooleanField(default=False, verbose_name="Cooperative Member")
    
    # Signature
    signature_image = models.ImageField(upload_to='signatures/', blank=True, null=True)
    signature_data = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.names} {self.surname}"
    
    class Meta:
        verbose_name = "Registry Entry"
        verbose_name_plural = "Registry Entries"
        ordering = ['-created_at']