# crow_app/models.py
from django.db import models
from django.contrib.auth.models import User
import uuid

# Your existing models
class Room(models.Model):
    ROOM_TYPES = [('public', 'Public Room'), ('private', 'Private Room')]
    
    name = models.CharField(max_length=200)
    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hosted_rooms')
    room_type = models.CharField(choices=ROOM_TYPES, default='public', max_length=10)
    password = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class UserClass(models.Model):
    """Represents a class/group that users can belong to"""
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)  # e.g., "CS101", "MATH202"
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_classes')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = "User Classes"
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class ClassMembership(models.Model):
    """Tracks which users belong to which classes"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='class_memberships')
    user_class = models.ForeignKey(UserClass, on_delete=models.CASCADE, related_name='members')
    date_joined = models.DateTimeField(auto_now_add=True)
    role = models.CharField(max_length=20, choices=[
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('assistant', 'Assistant'),
        ('member', 'Member')
    ], default='student')
    
    class Meta:
        unique_together = ['user', 'user_class']
    
    def __str__(self):
        return f"{self.user.username} in {self.user_class.code}"



class Meeting(models.Model):
    title = models.CharField(max_length=200)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='meetings')
    scheduled_time = models.DateTimeField()
    duration = models.IntegerField(default=60)
    created_at = models.DateTimeField(auto_now_add=True)
    participants = models.ManyToManyField(User, through='MeetingParticipant')
    allowed_classes = models.ManyToManyField(UserClass, blank=True, related_name='meetings')
    restrict_to_classes = models.BooleanField(default=False) 
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

class UserProfile(models.Model):
    THEME_CHOICES = [('light', 'Light'), ('dark', 'Dark'), ('auto', 'Auto')]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    timezone = models.CharField(max_length=50, default='UTC')
    phone_number = models.CharField(max_length=20, blank=True)
    company = models.CharField(max_length=100, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    theme_preference = models.CharField(choices=THEME_CHOICES, default='light', max_length=20)
    default_join_with_video = models.BooleanField(default=True)
    default_mute_on_join = models.BooleanField(default=False)
    default_meeting_duration = models.IntegerField(default=60)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"

# NEW: WebRTC Meeting Room Model
class MeetingRoom(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name='webrtc_hosted_rooms')
    participants = models.ManyToManyField(User, related_name='webrtc_joined_rooms', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    max_participants = models.IntegerField(default=10)
    
    def __str__(self):
        return f"{self.name} (Host: {self.host.username})"
