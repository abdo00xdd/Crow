# FIXED views.py - Copy this to replace your current views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout as auth_logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import IntegrityError  # FIX: Added missing import
from django.db.models import Q  # FIX: Added for query filtering
from .models import ClassMembership, Room, Meeting, Contact, UserClass, UserProfile, MeetingRoom
import json
import requests
from django.views.decorators.csrf import csrf_exempt
from .ai_service import gemini_service, AI_SERVICE_AVAILABLE

# ===== AI CHATBOT VIEWS =====
@login_required
def ai_chatbot(request):
    """Main AI chatbot page"""
    return render(request, 'ai_chatbot.html')



@csrf_exempt
@login_required
def ai_chat_api(request):
    """API endpoint to handle AI chat requests"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return JsonResponse({'error': 'Message is required'}, status=400)
        
        # Check if AI service is available (using the imported variable)
        if not AI_SERVICE_AVAILABLE:
            return JsonResponse({
                'response': "AI service is in fallback mode. Please configure a Gemini API key for full functionality.",
                'user_message': user_message,
                'ai_status': 'fallback'
            })
        
        # Prepare user context
        user_context = {
            'username': request.user.username,
        }
        
        # Get user's teams (classes)
        try:
            from .models import ClassMembership
            user_teams = ClassMembership.objects.filter(user=request.user).select_related('user_class')
            user_context['teams'] = [
                {
                    'name': membership.user_class.name,
                    'code': membership.user_class.code,
                    'role': membership.role
                }
                for membership in user_teams[:5]
            ]
        except Exception as e:
            user_context['teams'] = []
        
        # Get AI response
        ai_response = gemini_service.get_chat_response(user_message, user_context)
        
        return JsonResponse({
            'response': ai_response,
            'user_message': user_message,
            'ai_status': 'online' if not gemini_service.use_fallback else 'fallback'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON format'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def get_ai_response(message, user):
    """Get response from AI service"""
    message_lower = message.lower()
    
    # Meeting-related responses
    if any(word in message_lower for word in ['meeting', 'schedule', 'calendar']):
        return "I can help you with meetings! You can schedule meetings from the Calendar page, or create instant rooms from the dashboard."
    
    elif any(word in message_lower for word in ['video', 'camera', 'microphone']):
        return "For video settings, check your browser permissions. Make sure your camera and microphone are allowed for Crow."
    
    elif any(word in message_lower for word in ['class', 'join class', 'create class']):
        return "You can create or join classes from the Classes page. Classes help organize meetings by groups!"
    
    elif any(word in message_lower for word in ['contact', 'friend', 'invite']):
        return "You can add contacts from the Contacts page. Once added, you can invite them to meetings directly."
    
    elif any(word in message_lower for word in ['hello', 'hi', 'hey']):
        return f"Hello {user.username}! 👋 I'm Crow's AI assistant. How can I help you today?"
    
    elif any(word in message_lower for word in ['help', 'support']):
        return "I can help you with: scheduling meetings, technical issues, contact management, classes, and using Crow features."
    
    elif any(word in message_lower for word in ['thank', 'thanks']):
        return "You're welcome! Let me know if you need anything else. 🎯"
    
    elif any(word in message_lower for word in ['bye', 'goodbye']):
        return "Goodbye! Have a great day! 👋"
    
    # Default response
    return f"I understand you're asking about: '{message}'. I'm here to help with video meetings, scheduling, contacts, classes, and technical support. Could you tell me more?"

# ===== HOME VIEW =====
def home(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Get user profile
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


# ===== HELPER FUNCTIONS =====
def _create_meeting(room, host, title=None, scheduled_time=None, duration=None, participants=None):
    """Helper to create a meeting"""
    if title is None:
        title = f"Meeting - {room.name}"
    if scheduled_time is None:
        scheduled_time = timezone.now()
    if duration is None:
        try:
            duration = host.profile.default_meeting_duration
        except:
            duration = 60

    meeting = Meeting.objects.create(
        title=title,
        room=room,
        scheduled_time=scheduled_time,
        duration=duration,
    )
    meeting.participants.add(host)
    if participants:
        for p in participants:
            try:
                meeting.participants.add(p)
            except:
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
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
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

@login_required
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    return render(request, 'settings.html', {'profile': profile})

# ===== MEETING & ROOM VIEWS =====
@login_required
def create_room(request):
    """Create a new room"""
    if request.method == 'POST':
        name = request.POST.get('name')
        room_type = request.POST.get('room_type', 'public')
        password = request.POST.get('password')
        
        if not name:
            messages.error(request, 'Room name is required')
            return redirect('create_room')
        
        room = Room.objects.create(
            name=name,
            host=request.user,
            room_type=room_type,
            password=password if room_type == 'private' else None
        )
        
        # Create instant meeting
        _create_meeting(room=room, host=request.user)
        
        messages.success(request, f'Room "{name}" created successfully!')
        return redirect('room_detail', room_id=room.id)
    
    return render(request, 'create_room.html')

@login_required
def room_detail(request, room_id):
    """View room details"""
    room = get_object_or_404(Room, id=room_id)
    
    # Check password for private rooms
    if room.room_type == 'private' and room.host != request.user:
        if request.method == 'POST':
            password = request.POST.get('password')
            if password != room.password:
                messages.error(request, 'Incorrect password')
                return redirect('home')
        else:
            return render(request, 'room_password.html', {'room': room})
    
    meetings = Meeting.objects.filter(room=room).order_by('-scheduled_time')
    
    context = {
        'room': room,
        'meetings': meetings,
    }
    return render(request, 'room.html', context)

@login_required
def calendar_view(request):
    """Calendar view for scheduling and managing meetings"""
    from collections import defaultdict
    import json
    from datetime import datetime
    
    # Get user's teams
    user_classes = ClassMembership.objects.filter(user=request.user).select_related('user_class')
    
    # Handle POST requests
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # DELETE MEETING
        if action == 'delete':
            meeting_id = request.POST.get('meeting_id')
            try:
                meeting = Meeting.objects.get(id=meeting_id)
                
                # Check if user is the host (room owner)
                if meeting.room.host == request.user:
                    meeting_title = meeting.title
                    meeting.delete()
                    messages.success(request, f'Meeting "{meeting_title}" deleted successfully!')
                else:
                    messages.error(request, 'You do not have permission to delete this meeting')
            except Meeting.DoesNotExist:
                messages.error(request, 'Meeting not found')
            
            return redirect('calendar')
        
        # CREATE MEETING
        else:
            title = request.POST.get('title')
            scheduled_time = request.POST.get('scheduled_time')
            duration = request.POST.get('duration', 60)
            restrict_to_classes = request.POST.get('restrict_to_classes') == 'on'
            selected_class_ids = request.POST.getlist('allowed_classes')
            
            if not title or not scheduled_time:
                messages.error(request, 'Title and scheduled time are required')
                return redirect('calendar')
            
            try:
                # Create room for the meeting
                room = Room.objects.create(
                    name=f"{title} - Room",
                    host=request.user,
                    room_type='public'
                )
                
                # Create meeting
                meeting = Meeting.objects.create(
                    title=title,
                    room=room,
                    scheduled_time=scheduled_time,
                    duration=int(duration),
                    restrict_to_classes=restrict_to_classes
                )
                meeting.participants.add(request.user)
                
                # Add allowed teams
                if restrict_to_classes and selected_class_ids:
                    for class_id in selected_class_ids:
                        try:
                            user_class = UserClass.objects.get(id=class_id)
                            meeting.allowed_classes.add(user_class)
                        except UserClass.DoesNotExist:
                            pass
                
                messages.success(request, f'Meeting "{title}" scheduled successfully!')
                return redirect('calendar')
                
            except Exception as e:
                messages.error(request, f'Error scheduling meeting: {str(e)}')
                return redirect('calendar')
    
    # GET - Display calendar
    # Get upcoming meetings for the user
    meetings = Meeting.objects.filter(
        participants=request.user,
        scheduled_time__gte=timezone.now()
    ).order_by('scheduled_time').select_related('room')
    
    # Group meetings by date for calendar display (simplified - just title and time)
    meetings_by_date = defaultdict(list)
    
    # Group meetings with full data (including ID for deletion)
    meetings_data = defaultdict(list)
    
    for meeting in meetings:
        date_str = meeting.scheduled_time.strftime('%Y-%m-%d')
        time_str = meeting.scheduled_time.strftime('%H:%M')
        
        # Simplified for calendar grid display
        meetings_by_date[date_str].append({
            'title': meeting.title,
            'time': time_str,
        })
        
        # Full data for sidebar (includes ID)
        meetings_data[date_str].append({
            'id': meeting.id,
            'title': meeting.title,
            'time': time_str,
        })
    
    # Convert to JSON for JavaScript
    meetings_json = json.dumps(dict(meetings_by_date))
    meetings_data_json = json.dumps(dict(meetings_data))
    
    context = {
        'meetings': meetings,
        'meetings_json': meetings_json,
        'meetings_data': meetings_data_json,
        'user_classes': user_classes,
        'now': timezone.now(),
    }
    return render(request, 'calendar.html', context)
@login_required
def contacts_view(request):
    """View and manage contacts"""
    if request.method == 'POST':
        contact_username = request.POST.get('contact_username')
        
        try:
            contact_user = User.objects.get(username=contact_username)
            
            if contact_user == request.user:
                messages.error(request, 'You cannot add yourself as a contact')
            elif Contact.objects.filter(user=request.user, contact_user=contact_user).exists():
                messages.warning(request, 'Contact already added')
            else:
                Contact.objects.create(user=request.user, contact_user=contact_user)
                messages.success(request, f'Added {contact_username} to contacts')
        except User.DoesNotExist:
            messages.error(request, 'User not found')
        
        return redirect('contacts')
    
    contacts = Contact.objects.filter(user=request.user).select_related('contact_user')
    
    context = {
        'contacts': contacts,
    }
    return render(request, 'contacts.html', context)

@login_required
def instant_room(request):
    """Create an instant meeting room"""
    room = Room.objects.create(
        name=f"Instant Meeting - {request.user.username}",
        host=request.user,
        room_type='public'
    )

    _create_meeting(
        room=room, 
        host=request.user, 
        title=f"Instant - {request.user.username}", 
        scheduled_time=timezone.now()
    )

    return redirect('room_detail', room_id=room.id)

@login_required
def webrtc_video_room(request, room_id):
    """WebRTC Video Room"""
    try:
        # Try to get MeetingRoom (WebRTC room)
        room = MeetingRoom.objects.get(id=room_id)
    except:
        try:
            # Try to get regular Room
            room = Room.objects.get(id=room_id)
            # Convert to MeetingRoom
            meeting_room, created = MeetingRoom.objects.get_or_create(
                id=room_id,
                defaults={
                    'name': room.name,
                    'host': room.host,
                }
            )
            room = meeting_room
        except:
            # Create new MeetingRoom
            room = MeetingRoom.objects.create(
                id=room_id,
                name=f"Video Room - {room_id}",
                host=request.user
            )
    
    # Add user to participants
    if request.user not in room.participants.all():
        room.participants.add(request.user)
    
    return render(request, 'video_room.html', {
        'room': room,
        'user': request.user
    })

# ===== CLASS MANAGEMENT VIEWS =====
@login_required
def manage_classes(request):
    """View for managing user classes"""
    # FIX: Correct Q object usage
    user_classes = UserClass.objects.filter(
        Q(created_by=request.user) | 
        Q(members__user=request.user)
    ).distinct()
    
    # Classes user is a member of
    my_classes = UserClass.objects.filter(members__user=request.user)
    
    # Classes user created
    created_classes = UserClass.objects.filter(created_by=request.user)
    
    context = {
        'user_classes': user_classes,
        'my_classes': my_classes,
        'created_classes': created_classes,
    }
    return render(request, 'manage_classes.html', context)


# views.py - UPDATE ONLY THESE FUNCTIONS (keep everything else the same)
# Just change user-facing messages to say "team" instead of "class"

@login_required
def create_class(request):
    """Create a new team/department"""
    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code')
        description = request.POST.get('description', '')
        
        if not name or not code:
            messages.error(request, 'Team name and code are required')
            return redirect('create_class')
        
        try:
            # Create the team
            user_class = UserClass.objects.create(
                name=name,
                code=code.upper(),
                description=description,
                created_by=request.user
            )
            
            # Add creator as team manager
            ClassMembership.objects.create(
                user=request.user,
                user_class=user_class,
                role='teacher'  # Keep database value, just change UI display
            )
            
            messages.success(request, f'Team "{name}" created successfully!')
            return redirect('manage_classes')
            
        except IntegrityError:
            messages.error(request, 'Team code already exists')
            return redirect('create_class')
    
    return render(request, 'create_class.html')


@login_required
def join_class(request):
    """Join a team using code"""
    if request.method == 'POST':
        class_code = request.POST.get('class_code', '').upper().strip()
        
        try:
            user_class = UserClass.objects.get(code=class_code, is_active=True)
            
            # Check if already a member
            if ClassMembership.objects.filter(user=request.user, user_class=user_class).exists():
                messages.warning(request, f'You are already a member of {user_class.name}')
            else:
                # Join the team
                ClassMembership.objects.create(
                    user=request.user,
                    user_class=user_class,
                    role='student'  # Keep database value, just change UI display
                )
                messages.success(request, f'Successfully joined {user_class.name}!')
            
            return redirect('manage_classes')
            
        except UserClass.DoesNotExist:
            messages.error(request, 'Team not found or is inactive')
            return redirect('manage_classes')
    
    return redirect('manage_classes')


@login_required
def class_detail(request, class_id):
    """View team details and members"""
    user_class = get_object_or_404(UserClass, id=class_id)
    
    # Check if user is a member
    is_member = ClassMembership.objects.filter(
        user=request.user, 
        user_class=user_class
    ).exists()
    
    # Check if user has permission to view
    if not is_member and user_class.created_by != request.user:
        messages.error(request, 'You do not have permission to view this team')
        return redirect('manage_classes')
    
    members = ClassMembership.objects.filter(user_class=user_class).select_related('user')
    meetings = Meeting.objects.filter(allowed_classes=user_class).order_by('-scheduled_time')[:10]
    
    context = {
        'user_class': user_class,
        'is_member': is_member,
        'members': members,
        'meetings': meetings,
    }
    return render(request, 'class_detail.html', context)