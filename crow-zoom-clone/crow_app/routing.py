# crow_app/routing.py
from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/video/<str:room_id>/', consumers.VideoCallConsumer.as_asgi()),
]