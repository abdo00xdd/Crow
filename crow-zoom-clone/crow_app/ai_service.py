# crow_app/ai_service.py

import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class GeminiAIService:
    def __init__(self):
        self.client = None
        self.use_fallback = True
        self.api_key = getattr(settings, "GEMINI_API_KEY", None)

        if not self.api_key:
            print("No GEMINI_API_KEY found.")
            return

        try:
            from google import genai

            self.client = genai.Client(api_key=self.api_key)

            # Quick test call
            response = self.client.models.generate_content(
                model="gemini-1.5-flash",
                contents="Reply only with OK"
            )

            if response and response.text:
                self.use_fallback = False
                print("Gemini initialized successfully.")
            else:
                print("Gemini returned empty test response.")

        except Exception as e:
            print("Gemini init failed:", e)
            self.use_fallback = True

    def get_chat_response(self, message, context=None):
        if self.use_fallback or not self.client:
            return self._fallback(message, context)

        try:
            prompt = self._build_prompt(message, context)

            response = self.client.models.generate_content(
                model="gemini-2.0-pro",
                contents=prompt,
            )

            if response and response.text:
                return response.text.strip()

            return self._fallback(message, context)

        except Exception as e:
            print("Gemini runtime error:", e)
            return self._fallback(message, context)

    def _build_prompt(self, message, context):
        system = """
You are Crow AI, an intelligent assistant for a video conferencing platform.
Be helpful, natural, and conversational.
Answer clearly and concisely.
"""

        if context:
            if context.get("username"):
                system += f"\nUser: {context['username']}"

        return f"{system}\n\nUser question: {message}\nAnswer:"

    def _fallback(self, message, context=None):
        return "AI service is temporarily unavailable. Please try again."

# Singleton
gemini_service = GeminiAIService()
