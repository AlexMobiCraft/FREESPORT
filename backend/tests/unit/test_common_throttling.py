"""Unit-тесты proxy-aware throttling helpers."""

import pytest

from apps.common.throttling import ProxyAwareAnonRateThrottle, ProxyAwareUserRateThrottle


pytestmark = pytest.mark.unit


@pytest.mark.parametrize("throttle_cls", [ProxyAwareAnonRateThrottle, ProxyAwareUserRateThrottle])
@pytest.mark.parametrize(
    ("raw_ident", "expected_ident"),
    [
        ("[::1]:8080", "::1"),
        ("::ffff:192.0.2.1", "192.0.2.1"),
        ("fe80::1%eth0", "fe80::1"),
        (" 198.51.100.77 ", "198.51.100.77"),
    ],
)
def test_proxy_aware_throttle_sanitizes_to_canonical_ip(throttle_cls, raw_ident, expected_ident):
    """Throttle cache key использует canonical IP, а не raw variant из proxy header."""
    assert throttle_cls()._sanitize_ident(raw_ident) == expected_ident


def test_proxy_aware_throttle_falls_back_to_log_safe_value_for_invalid_ident():
    """Невалидный ident остается Redis-safe через log sanitizer."""
    assert ProxyAwareAnonRateThrottle()._sanitize_ident("bad\r\nip") == "bad\\r\\nip"
