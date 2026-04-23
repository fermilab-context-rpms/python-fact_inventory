"""Test IP address pool for parametrized IPv4/IPv6 testing.

This module defines a pool of test IP addresses using RFC-reserved ranges:
- IPv4: RFC 5737 TEST-NET-2 (192.0.2.0/24)
- IPv6: RFC 3849 documentation prefix (2001:db8::/32)

The pool generates paired IPv4/IPv6 addresses from a single offset definition,
ensuring test addresses are unique, predictable, and RFC-compliant.

parametrize_ipv4_ipv6 is a decorator factory that adds a pytest.mark.parametrize
to a test function, running it once with IPv4 addresses and once with IPv6.
It lives here because it is tightly coupled to IPAddressPool.
"""

from dataclasses import dataclass
from typing import ClassVar

import pytest

__all__ = [
    "IP_POOL",
    "IP_VERSION_4",
    "IP_VERSION_6",
    "IPAddressPool",
    "parametrize_ipv4_ipv6",
]

IP_VERSION_4 = "v4"
IP_VERSION_6 = "v6"


@dataclass(frozen=True)
class IPAddressPool:
    """Manages paired IPv4/IPv6 test addresses from RFC-reserved ranges.

    Attributes
    ----------
    ipv4_prefix : str
        Base IPv4 address for TEST-NET-2 (RFC 5737)
    ipv6_prefix : str
        Base IPv6 address for documentation prefix (RFC 3849)

    Notes
    -----
    Offsets are defined as (ipv4_octet, ipv6_suffix) tuples, where:
    - ipv4_octet: last octet of IPv4 address (0-255)
    - ipv6_suffix: hex suffix for IPv6 address (0-ffff)
    """

    ipv4_prefix: str = "192.0.2"
    ipv6_prefix: str = "2001:db8"

    # Offsets from base: (ipv4_octet, ipv6_suffix)
    #
    # Five named slots cover all test needs:
    # - first/second/third: general-purpose, used within a single test
    # - upsert: dedicated to upsert/replace semantics tests
    # - history: dedicated to retention and history-accumulation tests
    OFFSETS: ClassVar[dict[str, tuple[int, int]]] = {
        "first": (100, 0x1),
        "second": (101, 0x2),
        "third": (102, 0x3),
        "upsert": (200, 0x200),
        "history": (50, 0x50),
    }

    def ipv4(self, key: str) -> str:
        """Get IPv4 address for a given key.

        Parameters
        ----------
        key : str
            Address key from OFFSETS

        Returns
        -------
        str
            IPv4 address (e.g., "192.0.2.100")
        """
        offset = self.OFFSETS[key][0]
        return f"{self.ipv4_prefix}.{offset}"

    def ipv6(self, key: str) -> str:
        """Get IPv6 address for a given key.

        Parameters
        ----------
        key : str
            Address key from OFFSETS

        Returns
        -------
        str
            IPv6 address (e.g., "2001:db8::1")
        """
        offset = self.OFFSETS[key][1]
        return f"{self.ipv6_prefix}::{offset:x}"

    def as_dict(self, version: str) -> dict[str, str]:
        """Return all IP addresses as a dictionary for parametrization.

        Parameters
        ----------
        version : str
            Either "v4" for IPv4 or "v6" for IPv6

        Returns
        -------
        dict[str, str]
            Dictionary mapping keys to IP addresses

        Raises
        ------
        ValueError
            If version is not "v4" or "v6"
        """
        if version == IP_VERSION_4:
            method = self.ipv4
        elif version == IP_VERSION_6:
            method = self.ipv6
        else:  # pragma: no cover
            msg = f'version must be "v4" or "v6", got "{version}"'
            raise ValueError(msg)
        result: dict[str, str] = {}
        for key in self.OFFSETS:
            result[key] = method(key)
        return result


IP_POOL = IPAddressPool()


def parametrize_ipv4_ipv6(fixture_name: str = "test_ips"):
    """Decorator factory: parametrize a test with both IPv4 and IPv6 address dicts.

    Parameters
    ----------
    fixture_name : str, optional
        Name of the parameter injected into the test (default: "test_ips").

    Examples
    --------
    @parametrize_ipv4_ipv6()
    async def test_something(test_ips):
        ip = test_ips["first"]  # IPv4 or IPv6 depending on parametrization
    """
    return pytest.mark.parametrize(
        fixture_name,
        [IP_POOL.as_dict(IP_VERSION_4), IP_POOL.as_dict(IP_VERSION_6)],
        ids=["ipv4", "ipv6"],
    )
