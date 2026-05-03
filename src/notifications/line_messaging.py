class LineMessagingChannel:
    """Reserved for P3 LINE Messaging API support."""

    def send(self, user_id: str, subject: str, body: str, *, severity: str = "info") -> bool:
        return False
