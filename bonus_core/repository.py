from bonus_core.models import AIParsingQueue, Bonus, Game, GameProvider, QueueStatus


class BonusRepository:
    def create_bonus(self, **kwargs):
        return Bonus.objects.create(**kwargs)

    def get_active_bonuses(self):
        return Bonus.objects.filter(is_active=True, is_approved=True)

    def link_game_provider(self, provider_name, game_name):
        provider = None
        game = None
        if provider_name:
            provider, _ = GameProvider.objects.get_or_create(name=provider_name)
        if game_name and provider:
            game, _ = Game.objects.get_or_create(provider=provider, name=game_name)
        return provider, game


class AIParsingQueueRepository:
    def get_pending_queue_items(self):
        return AIParsingQueue.objects.filter(status=QueueStatus.PENDING).order_by("created_at")

    def update_queue_status(self, queue_item, status, error_message="", traceback_text=""):
        queue_item.status = status
        queue_item.error_message = error_message
        queue_item.traceback = traceback_text
        queue_item.save(update_fields=["status", "error_message", "traceback", "updated_at"])
        return queue_item
