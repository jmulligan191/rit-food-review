
"""Pytest tests for restaurants JSONC data.

These tests are self-contained and do not rely on a conftest.

Network tests are optional. To enable network checks set the environment
variable `RIT_TEST_NETWORK=1` before running pytest. Timeout can be set with
`RIT_TEST_TIMEOUT` (seconds, default 10).

Examples:
    RIT_TEST_NETWORK=1 pytest -q

"""
from __future__ import annotations

import logging
import os
from typing import Dict, Optional

import pytest

import requests

try:
    import json5
except Exception:
    json5 = None

LOGGER = logging.getLogger("rit.tests.restaurants")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def load_restaurants(path: Optional[str] = None) -> Dict:
    path = path or os.environ.get("RIT_RESTAURANTS_PATH", "compilation/static/restaurants.jsonc")
    if json5 is None:
        pytest.skip("json5 not installed; install with 'pip install json5'")
    p = path
    try:
        data = json5.loads(open(p, encoding="utf-8").read())
    except FileNotFoundError:
        pytest.skip(f"Restaurants data not found at {p}")
    if not isinstance(data, dict):
        pytest.skip("Restaurants data is not an object/dict at top-level")
    return data

def timeout_seconds() -> float:
    try:
        return float(os.environ.get("RIT_TEST_TIMEOUT", "10"))
    except Exception:
        return 10.0


def _head_or_get(url: str, timeout: float = 10.0):
    if requests is None:
        pytest.skip("requests not installed; install with 'pip install requests' or set RIT_TEST_NETWORK=0 to skip network tests")
    try:
        r = requests.head(url, timeout=timeout, allow_redirects=True)
        if r.status_code == 405:
            r = requests.get(url, timeout=timeout, stream=True, allow_redirects=True)
        return r
    except requests.RequestException as exc:
        LOGGER.debug("HTTP request failed for %s: %s", url, exc)
        return None


def _is_image_content_type(ct: Optional[str]) -> bool:
    return bool(ct and ct.strip().lower().startswith("image/"))


def test_website_slugs():
    """Verify website_slug endpoints are reachable (unless network disabled)."""
    # if not network_enabled():
    #     pytest.skip("Network tests disabled (set RIT_TEST_NETWORK=1 to enable)")
    data = load_restaurants()
    timeout = timeout_seconds()
    failures = []
    for slug, item in data.items():
        ws = item.get("website_slug")
        if not ws:
            continue
        url = f"https://www.rit.edu/dining/location/{ws}"
        LOGGER.info("Checking %s -> %s", slug, url)
        resp = _head_or_get(url, timeout=timeout)
        if resp is None:
            failures.append(f"{slug}: request failed for {url}")
            continue
        code = resp.status_code
        if code in (400, 404, 410):
            failures.append(f"{slug}: invalid website slug {ws} -> HTTP {code}")
        elif code >= 400:
            failures.append(f"{slug}: website slug returned HTTP {code}")

    assert not failures, "Website slug problems:\n" + "\n".join(failures)


def test_remote_images():
    """Verify remote image URLs return image content-types (unless network disabled)."""
    # if not network_enabled():
    #     pytest.skip("Network tests disabled (set RIT_TEST_NETWORK=1 to enable)")
    data = load_restaurants()
    timeout = timeout_seconds()
    failures = []
    for slug, item in data.items():
        for key in ("remote_logo_url", "remote_banner_url"):
            url = item.get(key)
            if not url:
                continue
            LOGGER.info("Checking image %s -> %s", slug, url)
            resp = _head_or_get(url, timeout=timeout)
            if resp is None:
                failures.append(f"{slug}: request failed for image {key} ({url})")
                continue
            if resp.status_code >= 400:
                failures.append(f"{slug}: image {key} returned HTTP {resp.status_code} for {url}")
                continue
            ct = resp.headers.get("content-type")
            if not _is_image_content_type(ct):
                try:
                    g = requests.get(url, timeout=timeout, stream=True) if requests is not None else None
                    if g is None or g.status_code >= 400:
                        failures.append(f"{slug}: image GET for {url} returned HTTP {getattr(g, 'status_code', 'no response')}")
                        continue
                    gct = g.headers.get("content-type")
                    if not _is_image_content_type(gct):
                        failures.append(f"{slug}: URL {url} did not return an image content-type (got: {gct})")
                except Exception as e:
                    failures.append(f"{slug}: image GET failed for {url}: {e}")

    assert not failures, "Image URL problems:\n" + "\n".join(failures)
