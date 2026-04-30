from django.contrib import admin
from .models import Guard, Visitor, GuestPass

admin.site.register(Guard)
admin.site.register(Visitor)
admin.site.register(GuestPass)