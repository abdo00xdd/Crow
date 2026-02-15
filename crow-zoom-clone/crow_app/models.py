# crow_app/models.py
from django.db import models
from django.contrib.auth.models import User
import uuid
from django.utils import timezone
from datetime import timedelta
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
class UserSession(models.Model):
    """Track user login sessions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    device_type = models.CharField(max_length=50, blank=True)  # Desktop, Mobile, Tablet
    browser = models.CharField(max_length=50, blank=True)
    location = models.CharField(max_length=200, blank=True)  # City, Country
    
    login_time = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    logout_time = models.DateTimeField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-login_time']
    
    def __str__(self):
        return f"{self.user.username} - {self.login_time.strftime('%Y-%m-%d %H:%M')}"
    
    def duration(self):
        """Get session duration"""
        end_time = self.logout_time or timezone.now()
        return end_time - self.login_time
    
    def is_online(self):
        """Check if session is currently active (last activity within 5 minutes)"""
        if not self.is_active:
            return False
        return (timezone.now() - self.last_activity) < timedelta(minutes=5)


class MeetingSession(models.Model):
    """Track individual meeting participation sessions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='meeting_sessions')
    meeting = models.ForeignKey('Meeting', on_delete=models.CASCADE, related_name='sessions')
    room = models.ForeignKey('Room', on_delete=models.CASCADE, related_name='sessions')
    
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    
    # Technical details
    connection_quality = models.CharField(max_length=20, choices=[
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
    ], default='good')
    
    # Participation metrics
    video_enabled_duration = models.IntegerField(default=0)  # seconds
    audio_enabled_duration = models.IntegerField(default=0)  # seconds
    screen_shared_duration = models.IntegerField(default=0)  # seconds
    
    # Device info
    device_type = models.CharField(max_length=50, blank=True)
    browser = models.CharField(max_length=50, blank=True)
    
    class Meta:
        ordering = ['-joined_at']
    
    def __str__(self):
        return f"{self.user.username} in {self.meeting.title}"
    
    def duration(self):
        """Get session duration"""
        end_time = self.left_at or timezone.now()
        return end_time - self.joined_at
    
    def is_active(self):
        """Check if user is currently in meeting"""
        return self.left_at is None


class UserActivity(models.Model):
    """Track user activities for analytics"""
    ACTIVITY_TYPES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('meeting_created', 'Meeting Created'),
        ('meeting_joined', 'Meeting Joined'),
        ('meeting_left', 'Meeting Left'),
        ('team_created', 'Team Created'),
        ('team_joined', 'Team Joined'),
        ('contact_added', 'Contact Added'),
        ('settings_updated', 'Settings Updated'),
        ('profile_updated', 'Profile Updated'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPES)
    description = models.TextField(blank=True)
    
    # Related objects (optional)
    meeting = models.ForeignKey('Meeting', null=True, blank=True, on_delete=models.SET_NULL)
    room = models.ForeignKey('Room', null=True, blank=True, on_delete=models.SET_NULL)
    team = models.ForeignKey('UserClass', null=True, blank=True, on_delete=models.SET_NULL)
    
    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = "User Activities"
    
    def __str__(self):
        return f"{self.user.username} - {self.activity_type} at {self.timestamp}"


class OnlineUser(models.Model):
    """Track currently online users (real-time presence)"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='online_status')
    last_seen = models.DateTimeField(auto_now=True)
    current_page = models.CharField(max_length=200, blank=True)
    is_in_meeting = models.BooleanField(default=False)
    current_meeting = models.ForeignKey('Meeting', null=True, blank=True, on_delete=models.SET_NULL)
    
    class Meta:
        verbose_name = "Online User"
        verbose_name_plural = "Online Users"
    
    def __str__(self):
        return f"{self.user.username} - Last seen: {self.last_seen}"
    
    def is_online(self):
        """User is online if last_seen within 2 minutes"""
        return (timezone.now() - self.last_seen) < timedelta(minutes=2)
    
    @staticmethod
    def get_online_count():
        """Get count of currently online users"""
        threshold = timezone.now() - timedelta(minutes=2)
        return OnlineUser.objects.filter(last_seen__gte=threshold).count()
    
    @staticmethod
    def get_online_users():
        """Get list of currently online users"""
        threshold = timezone.now() - timedelta(minutes=2)
        return OnlineUser.objects.filter(last_seen__gte=threshold).select_related('user')
