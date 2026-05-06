from ai_parsing.services.parser_service import ParserService


class MessageConsumer:
    """Compatibility wrapper for queue-style scrape messages."""

    def consume_scrape_message(self, message):
        return ParserService().parse_single_scrape(message)
