# crow_app/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class VideoCallConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'video_room_{self.room_id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        print(f"✅ User connected to room {self.room_id}")
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        # Notify others
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_left',
                'user_id': self.channel_name,
            }
        )
        print(f"❌ User disconnected from room {self.room_id}")
    
    # Receive message from WebSocket
    async def receive(self, text_data):
        data = json.loads(text_data)
        
        # Broadcast to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'signal_message',
                'message': data,
                'sender_channel': self.channel_name,
            }
        )
    
    # Receive message from room group
    async def signal_message(self, event):
        message = event['message']
        sender = event['sender_channel']
        
        # Don't send back to sender
        if sender != self.channel_name:
            await self.send(text_data=json.dumps(message))
    
    async def user_left(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_left',
            'user_id': event['user_id']
        }))