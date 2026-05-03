from django.contrib import admin
from .models import Guard, Visitor, GuestPass, Resident

admin.site.register(Guard)
admin.site.register(Visitor)
admin.site.register(GuestPass)
admin.site.register(Resident)