class MessagePublisher:
    """No-op publisher for v1 shared-DB flow."""

    def publish_bonus_created(self, bonus):
        return {
            "bonus_id": bonus.id,
            "casino_id": bonus.casino_id,
            "type": bonus.type,
            "title": bonus.title,
            "geo": bonus.geo.code if bonus.geo_id else None,
        }
