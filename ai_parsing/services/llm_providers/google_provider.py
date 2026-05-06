import os

from ai_parsing.services.llm_providers.base import BaseLLMProvider


class GoogleProvider(BaseLLMProvider):
    def generate(self, prompt):
        import google.generativeai as genai

        api_key = self.config.api_key or os.environ.get("GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(self.config.model)
        response = model.generate_content(prompt)
        return getattr(response, "text", "") or ""
