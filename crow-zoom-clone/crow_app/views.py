from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout as auth_logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Room, Meeting, Contact, UserProfile
import json

# ===== HOME VIEW =====
def home(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Get user profile if exists
    profile = None
    if hasattr(request.user, 'profile'):
        profile = request.user.profile
    
    recent_meetings = Meeting.objects.filter(
        participants=request.user
    ).order_by('-scheduled_time')[:5]
    
    upcoming_meetings = Meeting.objects.filter(
        scheduled_time__gte=timezone.now(),
        participants=request.user
    ).order_by('scheduled_time')[:5]
    
    context = {
        'profile': profile,
        'recent_meetings': recent_meetings,
        'upcoming_meetings': upcoming_meetings,
    }
    return render(request, 'home.html', context)


# Helper: create a meeting for a room and add participants
def _create_meeting(room, host, title=None, scheduled_time=None, duration=None, participants=None):
    if title is None:
        title = f"Meeting - {room.name}"
    if scheduled_time is None:
        scheduled_time = timezone.now()
    if duration is None:
        # try to use host profile preference
        try:
            duration = host.profile.default_meeting_duration
        except Exception:
            duration = 60

    meeting = Meeting.objects.create(
        title=title,
        room=room,
        scheduled_time=scheduled_time,
        duration=duration,
    )
    # add host and any provided participants
    meeting.participants.add(host)
    if participants:
        for p in participants:
            try:
                meeting.participants.add(p)
            except Exception:
                pass
    return meeting

# ===== AUTHENTICATION VIEWS =====
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Create user profile
            UserProfile.objects.create(user=user)
            
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})

def logout_view(request):
    """Log out the user"""
    auth_logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('home')

# ===== PROFILE & SETTINGS =====
@login_required
def settings_view(request):
    # Get or create user profile
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        # Persist only simplified fields: email, bio, profile picture, and join/mute defaults
        email = request.POST.get('email', '').strip()
        bio = request.POST.get('bio', '').strip()
        default_join_with_video = True if request.POST.get('default_join_with_video') else False
        default_mute_on_join = True if request.POST.get('default_mute_on_join') else False

        if email:
            request.user.email = email
            request.user.save()

        profile.bio = bio
        profile.default_join_with_video = default_join_with_video
        profile.default_mute_on_join = default_mute_on_join

        if 'profile_picture' in request.FILES:
            profile.profile_picture = request.FILES['profile_picture']

        profile.save()

        messages.success(request, 'Settings updated successfully!')

        return redirect('settings')

    return render(request, 'settings.html', {'profile': profile})


# Simple profile view (URL references this)
@login_required
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    return render(request, 'settings.html', {'profile': profile})

# ===== MEETING & ROOM VIEWS =====
@login_required
def create_room(request):
    if request.method == 'POST':
        name = request.POST.get('room_name')
        room_type = request.POST.get('room_type', 'public')
        password = request.POST.get('room_password', '')
        room = Room.objects.create(
            name=name,
            host=request.user,
            room_type=room_type,
            password=password if password else None
        )

        # Create an immediate meeting for this room so Start/Schedule behave similarly
        meeting_title = request.POST.get('meeting_title') or f"Instant: {name} - {request.user.username}"
        meeting = _create_meeting(
            room=room,
            host=request.user,
            title=meeting_title,
            scheduled_time=timezone.now(),
            duration=request.POST.get('duration') and int(request.POST.get('duration')) or None,
        )

        messages.success(request, f'Room "{name}" created and meeting started.')
        return redirect('room_detail', room_id=room.id)
    return render(request, 'create_room.html')

@login_required
def room_detail(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    # Handle delete action (only host)
    if request.method == 'POST' and request.POST.get('delete_room'):
        if request.user != room.host:
            messages.error(request, 'Only the room host can delete this room.')
            return redirect('room_detail', room_id=room.id)
        room.delete()
        messages.success(request, f'Room "{room.name}" deleted.')
        return redirect('home')

    # Handle join action: create an instant Meeting and add participant
    if request.method == 'POST' and request.POST.get('join_room'):
        # create a short meeting and add the user as participant
        meeting = Meeting.objects.create(
            title=f"Instant: {room.name} - {request.user.username}",
            room=room,
            scheduled_time=timezone.now(),
            duration=60,
        )
        meeting.participants.add(request.user)
        messages.success(request, 'You joined the room.')
        return redirect('room_detail', room_id=room.id)

    # Check password for private rooms
    if room.room_type == 'private' and room.password:
        access_key = f'room_access_{room.id}'

        # Already granted in session
        if not request.session.get(access_key):
            if request.method == 'POST' and request.POST.get('password'):
                entered_password = request.POST.get('password')
                if entered_password == room.password:
                    request.session[access_key] = True
                else:
                    messages.error(request, 'Incorrect password')
                    return render(request, 'room.html', {'room': room, 'require_password': True})
            else:
                return render(request, 'room.html', {'room': room, 'require_password': True})

    # Gather room history (meetings) and members
    history_qs = room.meetings.order_by('-scheduled_time').all()
    members_qs = User.objects.filter(meeting__room=room).distinct()

    # Paginate history and members
    history_page_num = request.GET.get('history_page', 1)
    members_page_num = request.GET.get('members_page', 1)

    history_paginator = Paginator(history_qs, 5)
    members_paginator = Paginator(members_qs, 10)

    try:
        history = history_paginator.page(history_page_num)
    except (PageNotAnInteger, EmptyPage):
        history = history_paginator.page(1)

    try:
        members = members_paginator.page(members_page_num)
    except (PageNotAnInteger, EmptyPage):
        members = members_paginator.page(1)
    is_host = request.user == room.host

    context = {
        'room': room,
        'history': history,
        'members': members,
        'is_host': is_host,
    }

    return render(request, 'room.html', context)

# ===== CALENDAR & CONTACTS =====
@login_required
def calendar_view(request):
    # If scheduling form submitted, create Meeting server-side
    if request.method == 'POST':
        title = request.POST.get('title') or 'Scheduled Meeting'
        datetime_str = request.POST.get('datetime')
        duration = request.POST.get('duration') or '30'
        meeting_type = request.POST.get('meeting_type', 'team')

        # parse datetime-local value (YYYY-MM-DDTHH:MM)
        from django.utils.dateparse import parse_datetime
        scheduled = None
        if datetime_str:
            # parse and ensure timezone aware
            scheduled = parse_datetime(datetime_str)
            if scheduled is not None and timezone.is_naive(scheduled):
                scheduled = timezone.make_aware(scheduled, timezone.get_current_timezone())

        # Create or reuse a personal room for the user
        room_name = f"{request.user.username} - Personal"
        room, _ = Room.objects.get_or_create(host=request.user, name=room_name, defaults={'room_type': 'private'})

        # Create meeting only if scheduled datetime parsed
        if scheduled:
            meeting = Meeting.objects.create(
                title=title,
                room=room,
                scheduled_time=scheduled,
                duration=int(duration)
            )
            meeting.participants.add(request.user)
            messages.success(request, f'Meeting "{title}" scheduled for {scheduled.strftime("%Y-%m-%d %H:%M")}')
        else:
            messages.error(request, 'Invalid date/time for meeting.')

        return redirect('calendar')

    meetings = Meeting.objects.filter(participants=request.user).order_by('scheduled_time')

    # Group meetings by date for the calendar frontend
    meetings_by_date = {}
    for m in meetings:
        date_key = m.scheduled_time.date().isoformat()
        meetings_by_date.setdefault(date_key, []).append({
            'id': m.id,
            'time': m.scheduled_time.strftime('%H:%M'),
            'title': m.title,
            'type': 'team',
            'participants': m.participants.count(),
            'room': m.room.name,
        })

    meetings_json = json.dumps(meetings_by_date)
    return render(request, 'calendar.html', {'meetings': meetings, 'meetings_json': meetings_json})

@login_required
def contacts_view(request):
    contacts = Contact.objects.filter(user=request.user)
    return render(request, 'contacts.html', {'contacts': contacts})

# ===== AI CHATBOT =====
@login_required
def ai_chatbot(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '')
            
            # Simple AI responses
            responses = {
                'hello': 'Hello! How can I help with your meeting today?',
                'hi': 'Hi there! Ready for your next video call?',
                'schedule': 'You can schedule meetings from the Calendar page.',
                'create room': 'Click the "Create Room" button to start a new video room.',
                'help': 'I can help you schedule meetings, create rooms, and manage your video conferences.',
                'meeting': 'To join a meeting, enter the meeting ID or click on an upcoming meeting.',
                'settings': 'You can update your profile and preferences in the Settings page.',
            }
            
            # Check for keywords
            ai_response = "I'm your AI assistant. I can help you with scheduling meetings, creating rooms, and answering questions about Crow."
            
            for keyword, response in responses.items():
                if keyword in user_message.lower():
                    ai_response = response
                    break

            return JsonResponse({'response': ai_response})
        except Exception:
            return JsonResponse({'response': 'I encountered an error. Please try again.'}, status=500)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

# ===== ADDITIONAL VIEWS =====
@login_required
def instant_room(request):
    """Create an instant meeting room"""
    room = Room.objects.create(
        name=f"Instant Meeting - {request.user.username}",
        host=request.user,
        room_type='public'
    )

    # create an immediate meeting and add the host
    _create_meeting(room=room, host=request.user, title=f"Instant - {request.user.username}", scheduled_time=timezone.now())

    return redirect('room_detail', room_id=room.id)