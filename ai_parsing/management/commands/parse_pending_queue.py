from django.core.management.base import BaseCommand

from ai_parsing.services.parser_service import ParserService


class Command(BaseCommand):
    help = "Parse pending AI queue rows synchronously."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=None)
        parser.add_argument(
            "--provider",
            choices=("openai", "google", "anthropic", "script"),
            default=None,
            help="Force a parser provider for this run.",
        )

    def handle(self, *args, **options):
        results = ParserService().parse_pending_queue(limit=options["limit"], provider=options["provider"])
        count = sum(len(group) for group in results)
        self.stdout.write(self.style.SUCCESS("Created %s bonus rows" % count))
