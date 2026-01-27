from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Room(models.Model):
    ROOM_TYPES = [
        ('public', 'Public Room'),
        ('private', 'Private Room'),
    ]
    
    name = models.CharField(max_length=200)
    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hosted_rooms')
    room_type = models.CharField(max_length=10, choices=ROOM_TYPES, default='public')
    password = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class Meeting(models.Model):
    title = models.CharField(max_length=200)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='meetings')
    scheduled_time = models.DateTimeField()
    duration = models.IntegerField(default=60)  # in minutes
    participants = models.ManyToManyField(User, through='MeetingParticipant')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title

class MeetingParticipant(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['user', 'meeting']

class Contact(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contacts_owner')
    contact_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contacts')
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'contact_user']
        
        
from django.db.models.signals import post_save
from django.dispatch import receiver

# User Profile Extension
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True)
    timezone = models.CharField(max_length=50, default='UTC')
    phone_number = models.CharField(max_length=20, blank=True)
    company = models.CharField(max_length=100, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    theme_preference = models.CharField(max_length=20, default='light', choices=[
        ('light', 'Light'),
        ('dark', 'Dark'),
        ('auto', 'Auto')
    ])
    
    # Meeting preferences
    default_join_with_video = models.BooleanField(default=True)
    default_mute_on_join = models.BooleanField(default=False)
    default_meeting_duration = models.IntegerField(default=60)  # minutes
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"

# Signal to create profile when user is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()        