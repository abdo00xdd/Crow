# crow_app/consumers.py - WebRTC Signaling Server
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()

class VideoCallConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for WebRTC signaling
    Handles peer discovery, ICE candidates, and SDP exchange
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
        
        self.username = self.user.username
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Notify others that user joined
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_joined',
                'username': self.username,
                'channel_name': self.channel_name
            }
        )
    
    async def disconnect(self, close_code):
        # Notify others that user left
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_left',
                'username': self.username
            }
        )
        
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """
        Receive message from WebSocket
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            # Route message based on type
            if message_type == 'offer':
                await self.handle_offer(data)
            elif message_type == 'answer':
                await self.handle_answer(data)
            elif message_type == 'ice-candidate':
                await self.handle_ice_candidate(data)
            elif message_type == 'chat':
                await self.handle_chat(data)
            elif message_type == 'get-peers':
                await self.send_peer_list()
                
        except json.JSONDecodeError:
            print('Invalid JSON received')
    
    async def handle_offer(self, data):
        """Handle WebRTC offer from peer"""
        target = data.get('target')
        offer = data.get('offer')
        
        # Forward offer to target peer
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'webrtc_offer',
                'offer': offer,
                'sender': self.username,
                'target': target
            }
        )
    
    async def handle_answer(self, data):
        """Handle WebRTC answer from peer"""
        target = data.get('target')
        answer = data.get('answer')
        
        # Forward answer to target peer
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'webrtc_answer',
                'answer': answer,
                'sender': self.username,
                'target': target
            }
        )
    
    async def handle_ice_candidate(self, data):
        """Handle ICE candidate from peer"""
        target = data.get('target')
        candidate = data.get('candidate')
        
        # Forward ICE candidate to target peer
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'ice_candidate',
                'candidate': candidate,
                'sender': self.username,
                'target': target
            }
        )
    
    async def handle_chat(self, data):
        """Handle chat message"""
        message = data.get('message')
        
        # Broadcast chat message to all peers
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender': self.username
            }
        )
    
    async def send_peer_list(self):
        """Send list of peers in room to requester"""
        # This would require tracking active connections
        # For now, we'll send a simple acknowledgment
        await self.send(text_data=json.dumps({
            'type': 'peer-list',
            'peers': []  # TODO: Implement peer tracking
        }))
    
    # Message handlers (called by channel layer)
    
    async def user_joined(self, event):
        """Someone joined the room"""
        username = event['username']
        
        # Don't notify self
        if username == self.username:
            return
        
        await self.send(text_data=json.dumps({
            'type': 'user-joined',
            'username': username
        }))
    
    async def user_left(self, event):
        """Someone left the room"""
        username = event['username']
        
        # Don't notify self
        if username == self.username:
            return
        
        await self.send(text_data=json.dumps({
            'type': 'user-left',
            'username': username
        }))
    
    async def webrtc_offer(self, event):
        """Forward WebRTC offer"""
        # Only send to target
        if event['target'] == self.username:
            await self.send(text_data=json.dumps({
                'type': 'offer',
                'offer': event['offer'],
                'sender': event['sender']
            }))
    
    async def webrtc_answer(self, event):
        """Forward WebRTC answer"""
        # Only send to target
        if event['target'] == self.username:
            await self.send(text_data=json.dumps({
                'type': 'answer',
                'answer': event['answer'],
                'sender': event['sender']
            }))
    
    async def ice_candidate(self, event):
        """Forward ICE candidate"""
        # Only send to target
        if event['target'] == self.username:
            await self.send(text_data=json.dumps({
                'type': 'ice-candidate',
                'candidate': event['candidate'],
                'sender': event['sender']
            }))
    
    async def chat_message(self, event):
        """Forward chat message"""
        # Don't send our own messages back
        if event['sender'] == self.username:
            return
        
        await self.send(text_data=json.dumps({
            'type': 'chat',
            'message': event['message'],
            'sender': event['sender']
        }))