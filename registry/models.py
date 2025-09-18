# registry/models.py
from django.db import models
from django.utils import timezone


class RegistryEntry(models.Model):
    names = models.CharField(max_length=100)
    surname = models.CharField(max_length=100)
    id_no_or_dob = models.CharField(max_length=50, blank=True, null=True)
    gender = models.CharField(max_length=20, choices=[
        ('Male', 'Male'), ('Female', 'Female'), ('LGBTQIA+', 'LGBTQIA+')
    ])
    disability = models.BooleanField("Disability (Yes/No)", default=False)
    physical_address = models.CharField(max_length=200)
    tish_area = models.CharField(max_length=100)  # Township/Informal/Hostel
    ward_no = models.CharField(max_length=20)
    contact_number = models.CharField(max_length=20)
    race = models.CharField(max_length=10, choices=[
        ('A', 'African'), ('I', 'Indian'), ('C', 'Coloured'), ('W', 'White')
    ])
    recovering_service_user = models.BooleanField(default=False)
    social_grant = models.CharField("Social Grant Recipient", max_length=20, choices=[
        ('None', 'None'), ('CSG', 'CSG'), ('SRD', 'SRD'), ('Other', 'Other')
    ])
    cooperative_member = models.BooleanField(default=False)
    signature_data = models.JSONField(null=True, blank=True)  # Stores drawing coordinates
    signature_image = models.ImageField(upload_to='signatures/', null=True, blank=True) 
    created_at = models.DateTimeField(auto_now_add=True)

    def get_race_display(self):
        return dict(self._meta.get_field('race').choices).get(self.race, self.race)
    
    def get_gender_display(self):
        return dict(self._meta.get_field('gender').choices).get(self.gender, self.gender)

    def __str__(self):
        return f"{self.names} {self.surname}"
