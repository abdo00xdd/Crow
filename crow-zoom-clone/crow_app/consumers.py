# crow_app/consumers.py - WebRTC Signaling Consumer

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

class VideoCallConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for WebRTC signaling
    Handles peer discovery and SDP/ICE exchange
    """
    
    async def connect(self):
        # Get room ID from URL
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'video_call_{self.room_id}'
        
        # Get user
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close()
            return
        
        self.user_id = str(self.user.id)
        self.username = self.user.username
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        print(f"✅ {self.username} connected to room {self.room_id}")
    
    async def disconnect(self, close_code):
        # Notify others that user left
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_left',
                'userId': self.user_id,
                'username': self.username
            }
        )
        
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        print(f"❌ {self.username} disconnected from room {self.room_id}")
    
    async def receive(self, text_data):
        """
        Receive message from WebSocket
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            print(f"📨 Received {message_type} from {self.username}")
            
            # Route message based on type
            if message_type == 'join':
                await self.handle_join(data)
            elif message_type == 'offer':
                await self.handle_offer(data)
            elif message_type == 'answer':
                await self.handle_answer(data)
            elif message_type == 'ice-candidate':
                await self.handle_ice_candidate(data)
                
        except json.JSONDecodeError:
            print('Invalid JSON received')
        except Exception as e:
            print(f'Error in receive: {e}')
    
    async def handle_join(self, data):
        """Handle user joining the room"""
        # Notify all others that this user joined
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_joined',
                'userId': self.user_id,
                'username': self.username,
                'exclude_self': self.channel_name
            }
        )
    
    async def handle_offer(self, data):
        """Forward WebRTC offer to target peer"""
        target = data.get('target')
        offer = data.get('offer')
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'webrtc_offer',
                'offer': offer,
                'sender': self.user_id,
                'senderName': self.username,
                'target': target
            }
        )
    
    async def handle_answer(self, data):
        """Forward WebRTC answer to target peer"""
        target = data.get('target')
        answer = data.get('answer')
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'webrtc_answer',
                'answer': answer,
                'sender': self.user_id,
                'senderName': self.username,
                'target': target
            }
        )
    
    async def handle_ice_candidate(self, data):
        """Forward ICE candidate to target peer"""
        target = data.get('target')
        candidate = data.get('candidate')
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'ice_candidate_forward',
                'candidate': candidate,
                'sender': self.user_id,
                'target': target
            }
        )
    
    # Message handlers (called by channel layer)
    
    async def user_joined(self, event):
        """Notify about new user"""
        # Don't send to self
        if event.get('exclude_self') == self.channel_name:
            return
        
        await self.send(text_data=json.dumps({
            'type': 'user-joined',
            'userId': event['userId'],
            'username': event['username']
        }))
    
    async def user_left(self, event):
        """Notify about user leaving"""
        # Don't send to self
        if event['userId'] == self.user_id:
            return
        
        await self.send(text_data=json.dumps({
            'type': 'user-left',
            'userId': event['userId'],
            'username': event['username']
        }))
    
    async def webrtc_offer(self, event):
        """Forward WebRTC offer"""
        # Only send to target
        if event['target'] == self.user_id:
            await self.send(text_data=json.dumps({
                'type': 'offer',
                'offer': event['offer'],
                'sender': event['sender'],
                'senderName': event['senderName']
            }))
    
    async def webrtc_answer(self, event):
        """Forward WebRTC answer"""
        # Only send to target
        if event['target'] == self.user_id:
            await self.send(text_data=json.dumps({
                'type': 'answer',
                'answer': event['answer'],
                'sender': event['sender'],
                'senderName': event['senderName']
            }))
    
    async def ice_candidate_forward(self, event):
        """Forward ICE candidate"""
        # Only send to target
        if event['target'] == self.user_id:
            await self.send(text_data=json.dumps({
                'type': 'ice-candidate',
                'candidate': event['candidate'],
                'sender': event['sender']
            }))