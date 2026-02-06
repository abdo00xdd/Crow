# crow_app/ai_service.py
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class GeminiAIService:
    def __init__(self):
        self.model = None
        self.use_fallback = True
        self.api_key = getattr(settings, "GEMINI_API_KEY", None)

        if not self.api_key:
            logger.warning("⚠️ GEMINI_API_KEY not set. Using fallback.")
            return

        try:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)

            # ✅ Use current supported model
            self.model = genai.GenerativeModel("gemini-1.5-flash")

            # Test request
            test = self.model.generate_content("Reply only with OK")
            if test and test.text:
                self.use_fallback = False
                logger.info("✅ Gemini AI initialized successfully")
            else:
                logger.warning("⚠️ Gemini test response empty")

        except ImportError:
            logger.error("❌ google-generativeai not installed")
        except Exception as e:
            logger.error(f"❌ Gemini init failed: {e}")

    def get_chat_response(self, user_message, user_context=None):
        if self.use_fallback or not self.model:
            return self._fallback(user_message, user_context)

        try:
            prompt = self._build_prompt(user_message, user_context)
            response = self.model.generate_content(prompt)

            if response and response.text:
                return response.text.strip()

            return self._fallback(user_message, user_context)

        except Exception as e:
            logger.error(f"Gemini runtime error: {e}")
            return self._fallback(user_message, user_context)

    def _build_prompt(self, message, context):
        system = (
            "You are Crow AI, a helpful assistant for a video conferencing platform.\n"
            "Keep answers short (2–3 sentences).\n"
        )

        if context:
            if context.get("username"):
                system += f"\nUser: {context['username']}"
            if context.get("teams"):
                teams = ", ".join(t["name"] for t in context["teams"][:3])
                system += f"\nTeams: {teams}"

        return f"{system}\n\nUser question: {message}\nAnswer:"

    def _fallback(self, message, context=None):
        msg = message.lower()

        if any(w in msg for w in ["hi", "hello", "hey"]):
            name = context.get("username", "there") if context else "there"
            return f"Hello {name}! 👋 How can I help you with Crow?"

        if any(w in msg for w in ["meeting", "schedule"]):
            return "You can schedule meetings from the Calendar page or create instant rooms from the dashboard."

        if any(w in msg for w in ["video", "camera", "mic"]):
            return "Check browser permissions and ensure no other app is using your camera or microphone."

        return "I'm here to help with meetings, teams, and technical issues. What do you need?"

# Singleton
gemini_service = GeminiAIService()
