from django.urls import path
from . import views

urlpatterns = [
    # Home
    path('', views.home, name='home'),
    path('profile/', views.profile_view, name='profile'),
    # Authentication
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # Rooms & Meetings
    path('create-room/', views.create_room, name='create_room'),
    path('room/<int:room_id>/', views.room_detail, name='room_detail'),
    path('instant-room/', views.instant_room, name='instant_room'),
    
    # Features
    path('calendar/', views.calendar_view, name='calendar'),
    path('contacts/', views.contacts_view, name='contacts'),
    path('settings/', views.settings_view, name='settings'),
    path('ai-chatbot/', views.ai_chatbot, name='ai_chatbot'),
]