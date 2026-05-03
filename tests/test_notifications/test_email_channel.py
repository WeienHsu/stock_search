from src.notifications.email import _normalize_smtp_password


def test_normalize_gmail_app_password_removes_group_spaces():
    assert _normalize_smtp_password("smtp.gmail.com", "abcd efgh ijkl mnop") == "abcdefghijklmnop"


def test_normalize_non_gmail_smtp_password_preserves_internal_spaces():
    assert _normalize_smtp_password("smtp.example.com", " abc def ") == "abc def"
