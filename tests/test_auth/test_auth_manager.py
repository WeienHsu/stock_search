import pytest

from src.auth.auth_manager import authenticate, register_user, user_exists


@pytest.fixture
def db(tmp_path):
    return tmp_path / "auth_test.db"


def test_register_and_authenticate(db):
    user_id = register_user("alice", "secret123", db_path=db)
    assert user_id
    assert authenticate("alice", "secret123", db_path=db) == user_id


def test_wrong_password_returns_none(db):
    register_user("bob", "correct_pw", db_path=db)
    assert authenticate("bob", "wrong_pw", db_path=db) is None


def test_unknown_user_returns_none(db):
    assert authenticate("ghost", "pw", db_path=db) is None


def test_duplicate_username_raises(db):
    register_user("carol", "pw1234", db_path=db)
    with pytest.raises(ValueError, match="已存在"):
        register_user("carol", "other_pw", db_path=db)


def test_short_password_raises(db):
    with pytest.raises(ValueError, match="6"):
        register_user("dave", "12345", db_path=db)


def test_user_exists(db):
    assert not user_exists(db_path=db)
    register_user("eve", "pw1234", db_path=db)
    assert user_exists(db_path=db)
