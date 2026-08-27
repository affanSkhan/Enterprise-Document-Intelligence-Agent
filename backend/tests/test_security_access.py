from app.security.auth import create_access_token, decode_access_token


def test_access_token_round_trip():
    token = create_access_token(user_id="u1", tenant_id="t1", role="viewer")
    claims = decode_access_token(token)
    assert claims["sub"] == "u1"
    assert claims["tenant_id"] == "t1"
    assert claims["role"] == "viewer"


def test_tenant_claim_cannot_be_missing():
    from jose import jwt
    from app.security.auth import ALGORITHM
    from app.core.config import settings

    token = jwt.encode({"sub": "u1", "role": "viewer"}, settings.SECRET_KEY, algorithm=ALGORITHM)
    try:
        decode_access_token(token)
    except ValueError as exc:
        assert "claims" in str(exc)
    else:
        raise AssertionError("Token without tenant claim must be rejected")
