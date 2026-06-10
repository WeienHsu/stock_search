from fastapi import APIRouter

from server.routes import USER_ID
from src.repositories.inbox_repo import list_messages, mark_read, unread_count

router = APIRouter(tags=["inbox"])


@router.get("/inbox")
def get_inbox(limit: int = 50, unread_only: bool = False) -> dict:
    return {
        "messages": list_messages(USER_ID, unread_only=unread_only, limit=limit),
        "unread": unread_count(USER_ID),
    }


@router.post("/inbox/{message_id}/read")
def read_message(message_id: str) -> dict:
    mark_read(message_id)
    return {"ok": True}
