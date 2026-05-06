import os

from ai_parsing.services.llm_providers.base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    def generate(self, prompt):
        from openai import OpenAI

        api_key = self.config.api_key or os.environ.get("OPENAI_API_KEY")
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=self.config.model,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": "Extract casino bonus data as strict JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content or ""
