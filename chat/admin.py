from django.contrib import admin
from .models import ChatUserProfile, DirectMessage

admin.site.register(ChatUserProfile)
admin.site.register(DirectMessage)
