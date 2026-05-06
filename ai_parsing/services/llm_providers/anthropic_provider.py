import os

from ai_parsing.services.llm_providers.base import BaseLLMProvider


class AnthropicProvider(BaseLLMProvider):
    def generate(self, prompt):
        from anthropic import Anthropic

        api_key = self.config.api_key or os.environ.get("ANTHROPIC_API_KEY")
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model=self.config.model,
            max_tokens=4096,
            temperature=0,
            system="Extract casino bonus data as strict JSON only.",
            messages=[{"role": "user", "content": prompt}],
        )
        chunks = []
        for block in response.content:
            text = getattr(block, "text", None)
            if text:
                chunks.append(text)
        return "\n".join(chunks)
