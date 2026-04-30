from rest_framework import serializers
from .models import Visitor, Guard, GuestPass

class VisitorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Visitor
        # We can specify exactly which fields we want to expose to the internet
        fields = ['id', 'name', 'phone_number', 'person_to_meet', 'purpose', 'check_in_time', 'check_out_time']

class GuestPassSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuestPass
        fields = ['id', 'resident_name', 'visitor_name','purpose', 'visitor_phone', 'pass_code', 'is_used', 'created_at']
        
        # We tell DRF: "The user is only allowed to SEND resident_name, visitor_name, and phone. 
        # Django handles the rest automatically."
        read_only_fields = ['pass_code', 'is_used', 'created_at']        