from app.security import (
    hash_otp, hash_device_token, hash_session_token,
    make_device_token, make_otp, make_session_token,
)


def test_otp_format():
    assert len(make_otp()) == 6
    assert make_otp().isdigit()


def test_otp_hash_bound_to_challenge():
    assert hash_otp("challenge-a", "123456") != hash_otp("challenge-b", "123456")


def test_device_token_hash_is_stable_and_domain_separated():
    token = make_device_token()
    assert hash_device_token(token) == hash_device_token(token)
    assert hash_device_token(token) != hash_device_token(make_device_token())
    assert hash_device_token(token) != hash_session_token(token)


def test_session_tokens_are_unique_and_prefixed():
    first = make_session_token()
    second = make_session_token()
    assert first.startswith("dbs_")
    assert first != second
    assert hash_session_token(first) != hash_session_token(second)
