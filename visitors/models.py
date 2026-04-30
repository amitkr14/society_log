from django.db import models
from django.contrib.auth.models import User
import random
import string

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
    
class GuestPass(models.Model):
    PURPOSE_CHOICES = [
        ('Delivery', 'Delivery'),
        ('Meeting', 'Meeting'),
        ('Maintenance', 'Maintenance'),
        ('Personal Visit', 'Personal Visit'),
        ('Other', 'Other'),
    ]
    resident_name = models.CharField(max_length=100, help_text="The resident who created this pass")
    visitor_name = models.CharField(max_length=100)
    visitor_phone = models.CharField(max_length=15)
    purpose = models.CharField(
        max_length=50, 
        choices=PURPOSE_CHOICES, 
        default='Delivery'
    )
    other_purpose = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        help_text="Please specify if purpose is 'Other'"
    )
    # We use the helper function here. unique=True ensures no two passes ever share a code!
    pass_code = models.CharField(max_length=6, default=generate_pass_code, unique=True)
    
    # This prevents a code from being used twice
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        status = "USED" if self.is_used else "VALID"
        return f"{self.pass_code} ({status}) - {self.visitor_name} visiting {self.resident_name}"    