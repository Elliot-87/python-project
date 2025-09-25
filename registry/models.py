from django.db import models

class RegistryEntry(models.Model):
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('LGBTQ+', 'LGBTQ+'),
        ('Other', 'Other'),
    ]
    RACE_CHOICES = [
        ('African', 'African'),
        ('Coloured', 'Coloured'),
        ('White', 'White'),
        ('Indian', 'Indian'),
    ]

    TISH_CHOICES = [
    ('Hostel', 'Hostel'),
    ('Informal Settlement', 'Informal Settlement'),
    ('Township', 'Township'),
    ]

    
    GRANT_CHOICES = [
        ('None', 'None'),
        ('Old Age Pension', 'Old Age Pension'),
        ('Disability Grant', 'Disability Grant'),
        ('Child Grant', 'Child Grant'),
        ('SRD', 'SRD'),
        ('CSG', 'CSG'),
    ]
    created_at = models.DateTimeField(auto_now_add=True)
    names = models.CharField(max_length=200)
    surname = models.CharField(max_length=200)
    id_no_or_dob = models.CharField(max_length=50)
    physical_address = models.TextField(blank=True, null=True)
    ward_no = models.CharField(max_length=50, blank=True, null=True)
    contact_number = models.CharField(max_length=50, blank=True, null=True)
    
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True, null=True)
    race = models.CharField(max_length=50, choices=RACE_CHOICES, blank=True, null=True)
    tish_area = models.CharField(
    max_length=50,
    choices=TISH_CHOICES,
    default='Hostel'
)

    social_grant = models.CharField(max_length=100, choices=GRANT_CHOICES, blank=True, null=True)
    
    disability = models.BooleanField(default=False)
    recovering_service_user = models.BooleanField(default=False)
    cooperative_member = models.BooleanField(default=False)

    signature_image = models.FileField(upload_to='signatures/', blank=True, null=True)
    
    try:
        from django.db.models import JSONField
    except ImportError:
        from django.contrib.postgres.fields import JSONField
    signature_data = JSONField(blank=True, null=True)

    def __str__(self):
        return f"{self.names} {self.surname}"
