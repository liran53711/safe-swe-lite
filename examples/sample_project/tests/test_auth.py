from src.auth import authenticate


def test_valid_credentials():
    assert authenticate("admin", "secret123") is True


def test_invalid_credentials():
    assert authenticate("admin", "wrong") is False


def test_empty_username():
    assert authenticate("", "secret123") is False
