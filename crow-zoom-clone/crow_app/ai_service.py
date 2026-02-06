# crow_app/ai_service.py - FIXED VERSION
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class GeminiAIService:
    def __init__(self):
        """Initialize Gemini AI or use fallback"""
        self.model = None
        self.use_fallback = True  # Default to fallback mode
        self.api_key = getattr(settings, 'GEMINI_API_KEY', None)
        
        # Check if we have a valid API key
        if self.api_key and self.api_key != 'dummy-key-for-testing' and len(self.api_key) > 10:
            try:
                # Try to import and configure Gemini
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                
                # Initialize the model
                self.model = genai.GenerativeModel('gemini-pro')
                
                # Test the connection with a simple request
                test_response = self.model.generate_content("Say 'OK' if you're working")
                if test_response and test_response.text:
                    self.use_fallback = False
                    logger.info("✅ Gemini AI service initialized successfully")
                else:
                    logger.warning("⚠️ Gemini responded but with empty content")
                    self.use_fallback = True
                    
            except ImportError as e:
                logger.error(f"❌ Failed to import google.generativeai: {str(e)}")
                logger.error("Run: pip install google-generativeai --break-system-packages")
                self.use_fallback = True
            except Exception as e:
                logger.error(f"❌ Failed to initialize Gemini: {str(e)}")
                logger.error("Check your API key and internet connection")
                self.use_fallback = True
        else:
            logger.warning("⚠️ No valid Gemini API key found. Using fallback responses.")
            if not self.api_key:
                logger.warning("Set GEMINI_API_KEY in settings.py")
    
    def get_chat_response(self, user_message, user_context=None):
        """
        Get AI response from Gemini or use fallback
        """
        # Always use fallback if model isn't initialized
        if self.use_fallback or self.model is None:
            logger.info("Using fallback response")
            return self._get_fallback_response(user_message, user_context)
        
        try:
            # Create enhanced prompt with context
            prompt = self._create_prompt(user_message, user_context)
            
            # Generate response
            response = self.model.generate_content(prompt)
            
            if response and response.text:
                return response.text.strip()
            else:
                logger.warning("Empty response from Gemini, using fallback")
                return self._get_fallback_response(user_message, user_context)
            
        except Exception as e:
            logger.error(f"Gemini error: {str(e)}")
            return self._get_fallback_response(user_message, user_context)
    
    def _create_prompt(self, user_message, user_context=None):
        """Create enhanced prompt for Gemini"""
        system_context = """You are Crow AI, a helpful assistant for the Crow video conferencing platform.

About Crow:
- Video conferencing platform (like Zoom/Google Meet)
- Features: video calls, meeting scheduling, team management, calendar integration
- Users can create and join teams for organized collaboration
- WebRTC-based real-time video communication

Your role:
- Help users with meetings, scheduling, and platform features
- Provide clear, concise, friendly responses
- Guide users to appropriate pages when needed
- Troubleshoot technical issues

Keep responses SHORT (2-3 sentences max) unless more detail is requested."""
        
        # Add user context if available
        if user_context:
            context_info = []
            if user_context.get('username'):
                context_info.append(f"User: {user_context['username']}")
            if user_context.get('teams'):
                team_names = [t['name'] for t in user_context['teams'][:3]]
                if team_names:
                    context_info.append(f"User's teams: {', '.join(team_names)}")
            
            if context_info:
                system_context += "\n\nCurrent context:\n" + "\n".join(context_info)
        
        # Combine system context with user message
        full_prompt = f"{system_context}\n\nUser question: {user_message}\n\nRespond helpfully:"
        
        return full_prompt
    
    def _get_fallback_response(self, user_message, user_context=None):
        """Enhanced fallback responses when Gemini is not available"""
        message_lower = user_message.lower()
        
        # Greeting
        if any(word in message_lower for word in ['hello', 'hi', 'hey', 'greetings']):
            username = user_context.get('username', 'there') if user_context else 'there'
            return f"Hello {username}! 👋 I'm Crow AI. I can help you with meetings, scheduling, teams, and video conferencing. What do you need help with?"
        
        # Meeting/Scheduling
        elif any(word in message_lower for word in ['meeting', 'schedule', 'calendar', 'book']):
            return "To schedule a meeting, go to the **Calendar** page from the navigation menu. You can set the date, time, duration, and even restrict it to specific teams. For instant meetings, use the 'Instant Room' button on the dashboard!"
        
        # Video/Technical
        elif any(word in message_lower for word in ['video', 'camera', 'microphone', 'audio', 'sound']):
            return "For video/audio issues: 1) Check your browser permissions (camera & mic must be allowed), 2) Make sure no other app is using your camera, 3) Try refreshing the page. Still having trouble? Check your device settings or try a different browser."
        
        # Teams/Classes
        elif any(word in message_lower for word in ['team', 'class', 'department', 'group']):
            return "Manage teams from the **Teams** page! You can create new teams, join existing ones using team codes, and organize meetings by department. Restrict meetings to specific teams for privacy and better organization."
        
        # Contacts
        elif any(word in message_lower for word in ['contact', 'friend', 'invite', 'add people']):
            return "Add contacts from the **Contacts** page by searching for usernames. Once added, you can easily invite them to meetings and see their availability."
        
        # Delete/Remove
        elif any(word in message_lower for word in ['delete', 'remove', 'cancel']):
            return "To delete a meeting: Go to **Calendar**, click on the date with the meeting, and click the **Delete** button next to it. Only meeting creators can delete their meetings."
        
        # Help/Support
        elif any(word in message_lower for word in ['help', 'support', 'how', 'what can you']):
            return "I can help you with:\n• Scheduling and managing meetings\n• Creating and joining teams\n• Video/audio troubleshooting\n• Contact management\n• Using Crow features\n\nWhat specific topic would you like help with?"
        
        # Thanks
        elif any(word in message_lower for word in ['thank', 'thanks', 'appreciate']):
            return "You're very welcome! 😊 Let me know if you need anything else!"
        
        # Goodbye
        elif any(word in message_lower for word in ['bye', 'goodbye', 'see you']):
            return "Goodbye! Have productive meetings! 👋"
        
        # Account/Profile
        elif any(word in message_lower for word in ['account', 'profile', 'settings']):
            return "Manage your account in **Settings** where you can update your email, profile picture, bio, and meeting preferences. You can also set default video/audio options there."
        
        # Default response
        return f"I'm here to help with Crow! I can assist with meetings, scheduling, teams, and troubleshooting. Could you rephrase your question or ask about a specific feature? (Note: Full AI is currently in fallback mode)"

# Create a singleton instance
gemini_service = GeminiAIService()
AI_SERVICE_AVAILABLE = not gemini_service.use_fallback

# Log initialization status
if AI_SERVICE_AVAILABLE:
    logger.info("🤖 Gemini AI is ONLINE and ready")
else:
    logger.warning("🤖 Gemini AI is OFFLINE - using fallback mode")