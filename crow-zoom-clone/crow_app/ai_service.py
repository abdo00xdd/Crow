# crow_app/ai_service.py
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class GeminiAIService:
    def __init__(self):
        """Initialize Gemini AI or use fallback"""
        self.model = None
        self.use_fallback = True  # Default to fallback mode
        self.api_key = getattr(settings, 'GEMINI_API_KEY', '')
        
        # Check if we have a valid API key
        if self.api_key and self.api_key != 'dummy-key-for-testing':
            try:
                # Try to import the new google.genai package
                import google.genai as genai
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-pro')
                self.use_fallback = False
                logger.info("✅ Gemini AI service initialized successfully with google.genai")
            except ImportError:
                # Try the old package as fallback
                try:
                    import google.generativeai as old_genai
                    old_genai.configure(api_key=self.api_key)
                    self.model = old_genai.GenerativeModel('gemini-pro')
                    self.use_fallback = False
                    logger.warning("⚠️ Using deprecated google.generativeai package. Please upgrade to google.genai")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize Gemini (old package): {str(e)}")
                    self.use_fallback = True
            except Exception as e:
                logger.error(f"❌ Failed to initialize Gemini: {str(e)}")
                self.use_fallback = True
        else:
            logger.warning("⚠️ No valid Gemini API key found. Using fallback responses.")
    
    def get_chat_response(self, user_message, user_context=None):
        """
        Get AI response from Gemini or use fallback
        """
        if self.use_fallback or self.model is None:
            return self._get_fallback_response(user_message)
        
        try:
            # Create system prompt
            system_prompt = self._create_system_prompt(user_context)
            full_prompt = f"{system_prompt}\n\nUser: {user_message}\nAssistant:"
            
            # Generate response
            response = self.model.generate_content(full_prompt)
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Gemini error: {str(e)}")
            return self._get_fallback_response(user_message)
    
    def _create_system_prompt(self, user_context=None):
        """Create system prompt for Crow assistant"""
        base_prompt = """You are Crow AI, an intelligent assistant for the Crow video conferencing application.

About Crow:
- A video meeting platform similar to Zoom
- Features: video calls, scheduling, team management, contacts
- Users can create/join teams
- Schedule meetings with calendar integration
- WebRTC-based video conferencing

Capabilities you can help with:
1. Meeting scheduling and management
2. Video conferencing setup and troubleshooting
3. Team management (creating, joining, managing members)
4. Contact management
5. Technical support for Crow features
6. General questions about video conferencing

Guidelines:
- Be helpful, friendly, and professional
- Keep responses concise but informative
- If you don't know something, admit it and suggest contacting support
- For technical issues, provide step-by-step guidance
- For scheduling, guide users to the calendar page
- For team management, guide users to the classes page

Current User Context:"""
        
        # Add user-specific context if available
        if user_context:
            context_lines = []
            if 'username' in user_context:
                context_lines.append(f"- Username: {user_context['username']}")
            if 'teams' in user_context and user_context['teams']:
                context_lines.append(f"- Teams: {len(user_context['teams'])}")
            
            if context_lines:
                base_prompt += "\n" + "\n".join(context_lines)
        
        return base_prompt
    
    def _get_fallback_response(self, user_message):
        """Fallback responses when Gemini is not available"""
        message_lower = user_message.lower()
        
        # Meeting-related
        if any(word in message_lower for word in ['meeting', 'schedule', 'calendar']):
            return "I can help you schedule meetings! Go to the Calendar page to create new meetings or view your upcoming ones. You can also create instant meetings from the dashboard."
        
        elif any(word in message_lower for word in ['video', 'camera', 'microphone']):
            return "For video issues, make sure your browser has camera and microphone permissions enabled. You can also check your device settings if the video isn't working."
        
        elif any(word in message_lower for word in ['class', 'team', 'department']):
            return "You can manage teams from the Classes page. Create new teams, join existing ones, or manage team members there!"
        
        elif any(word in message_lower for word in ['contact', 'friend', 'invite']):
            return "Add contacts from the Contacts page to easily invite people to your meetings."
        
        elif any(word in message_lower for word in ['hello', 'hi', 'hey']):
            return "Hello! 👋 I'm Crow AI. I can help you with meetings, scheduling, teams, and more!"
        
        elif any(word in message_lower for word in ['help', 'support']):
            return "I can help with: scheduling meetings, video setup, team management, contacts, and general questions about Crow!"
        
        elif 'thank' in message_lower:
            return "You're welcome! Let me know if you need anything else. 😊"
        
        elif any(word in message_lower for word in ['bye', 'goodbye']):
            return "Goodbye! Have a great day! 👋"
        
        # Default response
        return f"I understand you're asking about '{user_message}'. I'm here to help with video meetings, scheduling, and team collaboration. For more advanced AI responses, please add a Gemini API key to your settings."

# Create a singleton instance
gemini_service = GeminiAIService()
AI_SERVICE_AVAILABLE = not gemini_service.use_fallback