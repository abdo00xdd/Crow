# crow_app/urls.py - Add these URLs to your existing file

from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # Profile & Settings
    path('settings/', views.settings_view, name='settings'),
    path('profile/', views.profile_view, name='profile'),
    
    # Rooms & Meetings
    path('create-room/', views.create_room, name='create_room'),
    path('room/<int:room_id>/', views.room_detail, name='room_detail'),
    path('instant-room/', views.instant_room, name='instant_room'),
    path('calendar/', views.calendar_view, name='calendar'),
    path('contacts/', views.contacts_view, name='contacts'),
    
    # Video
    path('video/<uuid:room_id>/', views.webrtc_video_room, name='webrtc_video_room'),
    
    # AI Chatbot
    path('ai-chatbot/', views.ai_chatbot, name='ai_chatbot'),
    path('ai-chat-api/', views.ai_chat_api, name='ai_chat_api'),
    
    # ===== NEW: CLASS MANAGEMENT URLS =====
    path('classes/', views.manage_classes, name='manage_classes'),
    path('classes/create/', views.create_class, name='create_class'),
    path('classes/join/', views.join_class, name='join_class'),
    path('classes/<int:class_id>/', views.class_detail, name='class_detail'),

]
