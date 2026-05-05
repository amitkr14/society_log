from django.db import models
from django.contrib.auth.models import User
import random
import string
from django.utils import timezone
from datetime import timedelta

def generate_pass_code():
    # Generates a random 6-character code like "A7B9Q2"
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

class Guard(models.Model):
    # We link the Guard to Django's built-in User system...
    SHIFT_CHOICES = [
        ('Morning', 'Morning'),
        ('Evening', 'Evening'),
        ('Night', 'Night'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15)
    
    # ---> THIS IS THE MISSING PIECE <---
    shift = models.CharField(
        max_length=10, 
        choices=SHIFT_CHOICES, 
        default='Morning'
    )

    def __str__(self):
        return self.user.username    

class Visitor(models.Model):
    PURPOSE_CHOICES = [
        ('Delivery', 'Delivery'),
        ('Meeting', 'Meeting'),
        ('Maintenance', 'Maintenance'),
        ('Personal Visit', 'Personal Visit'),
        ('Other', 'Other'),
    ]

    name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    country = models.CharField(max_length=50, default="India")
    state = models.CharField(max_length=50, blank=True, null=True)
    district = models.CharField(max_length=50, blank=True, null=True)
    address_line = models.TextField(blank=True, null=True)
    person_to_meet = models.CharField(max_length=50, default='Amit')
    
    purpose = models.CharField(
        max_length=50, 
        choices=PURPOSE_CHOICES, 
        default='Delivery'
    )
    
    # ---> THIS IS THE MISSING FIELD! ADD THIS BACK <---
    other_purpose = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        help_text="Please specify if purpose is 'Other'"
    )
    
    check_in_time = models.DateTimeField(auto_now_add=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    
    checked_in_by = models.ForeignKey('Guard', on_delete=models.SET_NULL, null=True, related_name='check_ins')
    checked_out_by = models.ForeignKey('Guard', on_delete=models.SET_NULL, null=True, blank=True, related_name='check_outs')

    def __str__(self):
        if self.purpose == 'Other' and self.other_purpose:
            return f"{self.name} - {self.other_purpose}"
        return f"{self.name} - {self.purpose}"
    
class Resident(models.Model):
    # Link to Django's built-in User authentication system
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # Society-specific fields
    flat_number = models.CharField(max_length=20, help_text="e.g., A-402, B-105")
    phone_number = models.CharField(max_length=15)
    is_committee_member = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} (Flat {self.flat_number})"    
    
class GuestPass(models.Model):
    PURPOSE_CHOICES = [
        ('Delivery', 'Delivery'),
        ('Meeting', 'Meeting'),
        ('Maintenance', 'Maintenance'),
        ('Personal Visit', 'Personal Visit'),
        ('Other', 'Other'),
    ]
    
    # 1. THE FOREIGN KEY: Links directly to the logged-in resident's account
    resident = models.ForeignKey(Resident, on_delete=models.CASCADE, related_name='generated_passes',null=True, blank=True)
    
    visitor_name = models.CharField(max_length=100)
    visitor_phone = models.CharField(max_length=15)
    country = models.CharField(max_length=50, default="India")
    state = models.CharField(max_length=50, blank=True, null=True)
    district = models.CharField(max_length=50, blank=True, null=True)
    address_line = models.TextField(blank=True, null=True)
    purpose = models.CharField(max_length=50, choices=PURPOSE_CHOICES, default='Delivery')
    other_purpose = models.CharField(max_length=100, blank=True, null=True, help_text="Please specify if purpose is 'Other'")
    
    pass_code = models.CharField(max_length=6, default=generate_pass_code, unique=True)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # 2. THE TTL (Time-To-Live): Tracks exactly when this pass dies
    expires_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # Automatically set expiration to 24 hours from creation if not explicitly set
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    # 3. HELPER METHOD: Makes checking validity incredibly easy in our views later
    @property
    def is_valid(self):
        # Safety check: If it's an old test pass missing an expiry date, treat it as invalid
        if not self.expires_at:
            return False
            
        return not self.is_used and self.expires_at > timezone.now()

    def __str__(self):
        # Update the string representation to reflect the new logic
        status = "VALID" if self.is_valid else "USED/EXPIRED"
        return f"{self.pass_code} ({status}) - {self.visitor_name} visiting {self.resident.username}"