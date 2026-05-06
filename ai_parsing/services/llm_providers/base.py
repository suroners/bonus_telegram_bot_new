class BaseLLMProvider:
    def __init__(self, config):
        self.config = config

    def generate(self, prompt):
        raise NotImplementedError
