"""
Name: Request utilities
Path: core/sum_core/ops/request_utils.py
Purpose: Shared helpers for request metadata (client IP extraction).
Family: Ops/Observability.
Dependencies: Django, ipaddress
"""

from __future__ import annotations

import ipaddress
from collections.abc import Iterable

from django.conf import settings
from django.http import HttpRequest

TRUSTED_PROXY_SETTING = "SUM_TRUSTED_PROXY_IPS"
NetworkType = ipaddress.IPv4Network | ipaddress.IPv6Network


def _normalize_trusted_proxy_entries(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Iterable):
        return [str(entry) for entry in value if entry]
    return []


def _get_trusted_proxy_networks() -> list[NetworkType]:
    entries = _normalize_trusted_proxy_entries(
        getattr(settings, TRUSTED_PROXY_SETTING, [])
    )
    networks: list[NetworkType] = []
    for entry in entries:
        try:
            networks.append(ipaddress.ip_network(entry, strict=False))
        except ValueError:
            continue
    return networks


def _is_trusted_proxy(ip_address: str, networks: list[NetworkType]) -> bool:
    try:
        ip_value = ipaddress.ip_address(ip_address)
    except ValueError:
        return False
    return any(ip_value in network for network in networks)


def get_client_ip(request: HttpRequest) -> str:
    """
    Extract the client IP address from a request.

    Only trusts X-Forwarded-For if the request comes from a configured proxy.
    Configure trusted proxies via settings.SUM_TRUSTED_PROXY_IPS (IP/CIDR list).
    """
    remote_addr = request.META.get("REMOTE_ADDR", "")
    if not remote_addr:
        return ""

    trusted_networks = _get_trusted_proxy_networks()
    if not trusted_networks or not _is_trusted_proxy(remote_addr, trusted_networks):
        return str(remote_addr)

    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if not x_forwarded_for:
        return str(remote_addr)

    chain = [ip.strip() for ip in x_forwarded_for.split(",") if ip.strip()]
    if not chain:
        return str(remote_addr)

    chain.append(remote_addr)
    while chain and _is_trusted_proxy(chain[-1], trusted_networks):
        chain.pop()

    if not chain:
        return str(remote_addr)

    candidate_ip = chain[-1]
    try:
        validated_ip = ipaddress.ip_address(candidate_ip)
    except ValueError:
        return str(remote_addr)

    return str(validated_ip)
