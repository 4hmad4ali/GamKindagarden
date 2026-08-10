from django.db import models
from django.contrib.auth.models import User


class ChatUserProfile(models.Model):
    """پروفایل کاربر چت — عکس پروفایل و وضعیت آنلاین"""
    user            = models.OneToOneField(User, on_delete=models.CASCADE, related_name='chat_profile')
    profile_picture = models.ImageField(upload_to='chat_profiles/', null=True, blank=True)
    is_online       = models.BooleanField(default=False)
    last_seen       = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    @property
    def display_name(self):
        return self.user.get_full_name() or self.user.username

    @property
    def picture_url(self):
        if self.profile_picture:
            return self.profile_picture.url
        return None


class DirectMessage(models.Model):
    """پیام مستقیم بین دو کارمند"""
    sender     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sent')
    receiver   = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_received')
    content    = models.TextField()
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.username} → {self.receiver.username}: {self.content[:40]}"
