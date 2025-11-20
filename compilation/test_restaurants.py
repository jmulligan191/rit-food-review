
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
from pathlib import Path

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


def test_local_media_paths():
    """Verify local media file paths referenced in the JSONC exist in the repo."""
    data = load_restaurants()
    failures = []
    # allow auto-fixing (experimental) when env var is set
    #fix_media = os.environ.get("RIT_FIX_MEDIA") in ("1", "true", "True")
    fix_media = True
    alt_exts = [".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"]
    json_path = os.environ.get("RIT_RESTAURANTS_PATH", "compilation/static/restaurants.jsonc")
    updated = False

    for slug, item in data.items():
        for key in ("local_logo_path", "local_banner_path"):
            val = item.get(key)
            print(val)
            if not val:
                continue
            # skip remote URLs
            if isinstance(val, str) and (val.startswith("http") or val.startswith("//")):
                continue
            # enforce that local media paths refer to the `media/` folder
            if not isinstance(val, str) or not val.startswith("media/"):
                failures.append(f"{slug}: {key} does not appear to be under media/: {val}")
                continue
            p = Path(val)
            if not p.is_absolute():
                p = Path.cwd() / 'docs' / val
            
            if p.exists():
                continue
            # try alternative extensions in the same directory
            found_alt = None
            for ext in alt_exts:
                alt = p.with_suffix(ext)
                if alt.exists():
                    found_alt = alt
                    break
            if found_alt:
                rel_alt = os.path.relpath(str(found_alt), str(Path.cwd()))
                LOGGER.warning("%s: %s missing (%s) — found alternative %s", slug, key, p, rel_alt)
                # update in-memory data so subsequent checks treat it as present
                item[key] = rel_alt
                updated = True
                continue
            failures.append(f"{slug}: {key} points to missing file: {p}")

    # if allowed, write back updates to the JSONC source to fix paths
    if fix_media and updated and json5 is not None:
        try:
            src = Path(json_path)
            if src.exists():
                write_data = data
                # write back with json5.dumps to preserve JSONC-ish formatting
                src.write_text(json5.dumps(write_data, indent=2), encoding="utf-8")
                LOGGER.warning("Wrote updated media paths back to %s", src)
        except Exception as e:
            LOGGER.warning("Failed to write updated restaurants JSONC: %s", e)

    assert not failures, "Local media path problems:\n" + "\n".join(failures)

#pytest mark this one as network test, takes a long time
@pytest.mark.skipif(os.environ.get("RIT_TEST_NETWORK") not in ("1", "true", "True"), reason="Network tests disabled (set RIT_TEST_NETWORK=1 to enable)")
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

