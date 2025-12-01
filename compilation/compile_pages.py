
#!/usr/bin/env python3
"""Jinja-only compiler (final version).

This file intentionally contains only the Jinja2-based compiler and writes
rendered pages directly to the output folder (default `restaurants/`).
"""
import argparse
import json
from pathlib import Path
import json5
from datetime import datetime
import base64
import os

def load_jsonc(path: Path):
    """Load a JSONC file (JSON with comments) and return the parsed data."""
    data = json5.loads(path.read_text(encoding="utf-8"))
    return data

def choose_image(item: dict, local_key: str, remote_key: str) -> str:
    local = item.get(local_key)
    remote = item.get(remote_key)
    if local:
        return local
    return remote or ""


def _svg_placeholder(width: int = 600, height: int = 200, text: str = "No image") -> str:
    """Return a base64 data URI of a simple SVG placeholder with centered text."""
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="#e9ecef"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="#6c757d" font-family="Arial, Helvetica, sans-serif" font-size="24">{text}</text></svg>'''
    b = svg.encode('utf-8')
    return 'data:image/svg+xml;base64,' + base64.b64encode(b).decode('ascii')


def build_banner_html(item: dict, media_prefix: str = "", placeholder_if_missing: bool = True) -> str:
    """Build banner HTML, prefixing local media paths with `media_prefix`.

    `item` may contain `local_banner_path` (a local path like
    `media/images/...`) or `remote_banner_url`. If the chosen banner looks
    like a local path (doesn't start with http or //) prepend the provided
    `media_prefix` so the rendered page points to the correct location.
    """
    banner = choose_image(item, "local_banner_path", "remote_banner_url")
    if not banner:
        if not placeholder_if_missing:
            return ""
        # return a lightweight inline SVG placeholder so restaurant pages without banners still look intentional
        placeholder = _svg_placeholder(1200, 300, 'No banner available')
        return f'<div class="banner"><img src="{placeholder}" alt="{item.get("name","") } banner" class="img-fluid w-100 banner-img"/></div>'
    # if banner looks local (not http///) verify the file exists on disk; if it doesn't, treat as missing
    if not (banner.startswith("http") or banner.startswith("//")):
        # banner path is expected relative to repo root (e.g. media/images/...)
        if not Path(banner).exists():
            if not placeholder_if_missing:
                return ""
            placeholder = _svg_placeholder(1200, 300, 'No banner available')
            return f'<div class="banner"><img src="{placeholder}" alt="{item.get("name","") } banner" class="img-fluid w-100 banner-img"/></div>'
        banner = f"{media_prefix}{banner}"
    return f'<div class="banner"><img src="{banner}" alt="{item.get("name","")} banner" class="img-fluid w-100 banner-img"/></div>'

def main():
    p = argparse.ArgumentParser(description="Compile JSONC files into HTML pages using a Jinja template")
    p.add_argument("--restaurants", default="compilation/static/restaurants.jsonc", help="Path to the restaurants JSONC source file")
    p.add_argument("--homepage", default="compilation/static/homepage.jsonc", help="Path to the homepage JSONC source file (optional)")
    p.add_argument("--template", default="templates/skeleton.html", help="Path to base HTML template")
    p.add_argument("--out", default="docs", help="Output directory for generated pages (default: docs)")
    args = p.parse_args()

    restaurants_src = Path(args.restaurants)
    homepage_src = Path(args.homepage)
    template_path = Path(args.template)
    outdir = Path(args.out)

    if not restaurants_src.exists():
        print(f"Restaurants source file not found: {restaurants_src}")
        raise SystemExit(1)
    if not template_path.exists():
        print(f"Template file not found: {template_path}")
        raise SystemExit(1)

    # create restaurants folder in src if it doesn't exists already
    try:
        data = load_jsonc(restaurants_src)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSONC file {restaurants_src}: {e}")
        raise SystemExit(1)
    rest_out = outdir / "restaurants"
    rest_out.mkdir(parents=True, exist_ok=True)

    reviews_src = Path("compilation/static/reviews.jsonc")
    reviews_map = {}
    if reviews_src.exists():
        try:
            reviews_map = load_jsonc(reviews_src)
        except Exception as e:
            print(f"Warning: failed to load reviews from {reviews_src}: {e}")

    # create specific restaurant pages, collect summary for index
    cards = []
    try:
        from jinja2 import Environment, select_autoescape, FileSystemLoader
    except Exception:
        print("jinja2 is required. Install with: pip install jinja2")
        raise SystemExit(1)

    # future proofing this so we can have more templates later
    templates = {
        "skeleton": template_path.name,
        "restaurant": (template_path.parent / 'skeleton-resturaunts.html').name,
    }

    # Create a Jinja environment with a FileSystemLoader pointed at the templates folder
    env = Environment(loader=FileSystemLoader(str(template_path.parent)), autoescape=select_autoescape(["html", "xml"]))

    templates_jinja = {}
    for key, name in templates.items():
        try:
            templates_jinja[key] = env.get_template(name)
        except Exception:
            templates_jinja[key] = None
    
    # for convienence i'll just set them to variables cause the dict syntax every time we want a template is annoying
    skeleton = templates_jinja["skeleton"]
    skeleton_restaurant = templates_jinja["restaurant"]
    


    if not data or not isinstance(data, dict):
        print(f"Invalid or no restaurant data found in {restaurants_src}")
        raise SystemExit(1)

    for key, item in data.items():
        slug = item.get("slug") or key
        # parse ISO timestamps into datetime objects and expose epoch ms for client-side formatting
        def _attach_epoch(field: str):
            val = item.get(field)
            if isinstance(val, str) and val:
                try:
                    dt = datetime.fromisoformat(val)
                    # store epoch milliseconds for client-side JS formatting
                    item[f"{field}_epoch_ms"] = int(dt.timestamp() * 1000)
                    # keep parsed datetime object available (useful for server-side logic/tests)
                    item[f"{field}_parsed"] = dt
                except Exception:
                    # ignore parse errors and leave original value as-is
                    pass

        _attach_epoch('created_at')
        _attach_epoch('updated_at')
        # normalize hours: support wildcard keys like `everyday`, `weekdays`, `weekends`.
        # priority ordering: explicit day key (if present) -> weekday/weekend wildcard -> everyday wildcard -> None
        raw_hours = item.get('hours') or {}
        if isinstance(raw_hours, dict):
            days = ['monday','tuesday','wednesday','thursday','friday','saturday','sunday']
            effective = {}
            for d in days:
                if d in raw_hours:
                    # explicit day provided (may be None meaning closed)
                    val = raw_hours.get(d)
                else:
                    # fallback to weekdays/weekends/everyday
                    if d in ('monday','tuesday','wednesday','thursday','friday') and ('weekdays' in raw_hours):
                        val = raw_hours.get('weekdays')
                    elif d in ('saturday','sunday') and ('weekends' in raw_hours):
                        val = raw_hours.get('weekends')
                    elif 'everyday' in raw_hours:
                        val = raw_hours.get('everyday')
                    else:
                        val = raw_hours.get(d)

                # normalize common representations of a full-day / 24-7 schedule
                # and accept arrays of intervals (e.g., open in morning and evening)
                def _normalize_interval(s):
                    if not isinstance(s, str):
                        return s
                    v = s.strip().lower()
                    if (v in ('24/7', '24-7', '247', '24h', '24 hours', 'open 24/7', 'open 24 hours', 'always', 'all day')
                        or v == '12:00am-11:59pm' or v == '12:00 am - 11:59 pm' or v == '12:00am - 11:59pm'):
                        return 'Open 24/7'
                    return s

                if isinstance(val, list):
                    # a list of intervals — normalize each entry and collapse
                    normalized = [_normalize_interval(x) for x in val if x is not None]
                    # if any entry indicates 24/7, collapse to single label
                    if any((isinstance(n, str) and n == 'Open 24/7') for n in normalized):
                        effective[d] = 'Open 24/7'
                    else:
                        effective[d] = normalized
                elif isinstance(val, str) and val:
                    effective_val = _normalize_interval(val)
                    effective[d] = effective_val
                else:
                    # preserve None or other non-string markers (closed)
                    effective[d] = val

            # replace item.hours with the expanded mapping so templates can continue to use item.hours.get(day)
            item['hours'] = effective
        filename = rest_out / f"{slug}.html"
        # compute a media prefix so local media paths resolve correctly from the
        # rendered page's directory to the output `media/` folder.
        rel = os.path.relpath(str(outdir), str(filename.parent))
        media_prefix = (rel + "/") if rel != "." else ""
        site_prefix = media_prefix

        banner_html = build_banner_html(item, media_prefix)
        logo_url = choose_image(item, "local_logo_path", "remote_logo_url") or ""
        # if logo_url is local, verify file exists; if missing, clear so template will use placeholder
        if logo_url and not (logo_url.startswith('http') or logo_url.startswith('//')):
            if not Path(logo_url).exists():
                logo_url = ""
        # ensure payment_methods is a dict for template convenience (list -> dict of true)
        pm = item.get('payment_methods')
        if isinstance(pm, list):
            item['payment_methods'] = {str(x): True for x in pm}
        elif isinstance(pm, dict):
            # leave as-is
            pass
        else:
            item['payment_methods'] = {}

        # normalize tags to a list
        tags = item.get('tags')
        if isinstance(tags, str):
            item['tags'] = [t.strip() for t in tags.split(',') if t.strip()]
        elif isinstance(tags, list):
            item['tags'] = tags
        else:
            item['tags'] = []

        # official URL preference: prefer explicit `website_url`, then `website`, then `website_slug` fallback
        official_url = item.get('website_url') or item.get('website') or (('https://www.rit.edu/dining/location/' + item.get('website_slug')) if item.get('website_slug') else None)

        # provide a small logo placeholder data-uri so templates can show an inline logo when none provided
        logo_placeholder = _svg_placeholder(200, 200, 'No logo')
        # compute an online ordering URL if the data includes an ordering id
        ordering_id = item.get("online_ordering_id", None)
        ordering_url = None
        if ordering_id is not None:
            ordering_url = f"https://ondemand.rit.edu/?SE={ordering_id}"
        # attach reviews for this restaurant (if any)
        reviews = []
        try:
            # reviews_map keys are expected to be slugs
            raw_reviews = reviews_map.get(slug) or reviews_map.get(key) or []
            if isinstance(raw_reviews, list):
                # parse dates and attach epoch ms for each review; ignore parse errors
                for r in raw_reviews:
                    d = r.get("date")
                    if isinstance(d, str) and d:
                        try:
                            dt = datetime.fromisoformat(d)
                            r["date_parsed"] = dt
                            r["date_epoch_ms"] = int(dt.timestamp() * 1000)
                        except Exception:
                            r["date_parsed"] = None
                            r["date_epoch_ms"] = None
                # sort reviews by parsed date descending (newest first)
                reviews = sorted([r for r in raw_reviews if isinstance(r, dict)], key=lambda x: x.get("date_parsed") or datetime.min, reverse=True)
            else:
                reviews = []
        except Exception:
            reviews = []
        # use restaurant template for individual pages; pass media_prefix so
        # templates can prepend it for local media paths (e.g. "../"). Also
        # pass ordering_url (if any) so templates can show an Order Online link.
        rendered = skeleton_restaurant.render(item=item, page_title=item.get("name"), banner_html=banner_html, logo_url=logo_url, extra_content="", media_prefix=media_prefix, site_prefix=site_prefix, ordering_url=ordering_url, reviews=reviews, official_url=official_url, logo_placeholder=logo_placeholder)
        filename.write_text(rendered, encoding="utf-8")
        print(f"Wrote {filename}")

        # build card HTML for index
        card = {
            "name": item.get("name","Unnamed"),
            "description": item.get("description",""),
            "slug": slug,
            "logo": logo_url or item.get("local_logo_path") or item.get("remote_logo_url") or "",
        }
        cards.append(card)

    # restaurants index page (cards)
    cards_html = []
    # Cards are rendered into the restaurants index (which lives in the
    # `rest_out` directory). Compute media_prefix for that location so card
    # images point at the correct `media/` path.
    rel_cards = os.path.relpath(str(outdir), str(rest_out))
    cards_media_prefix = (rel_cards + "/") if rel_cards != "." else ""
    index_media_prefix = cards_media_prefix
    index_site_prefix = index_media_prefix
    for c in cards:
        if c["logo"]:
            if c["logo"].startswith("http") or c["logo"].startswith("//"):
                img = f'<img src="{c["logo"]}" class="card-img-top card-media-img" alt="{c["name"]} logo">'
            else:
                img = f'<img src="{cards_media_prefix}{c["logo"]}" class="card-img-top card-media-img" alt="{c["name"]} logo">'
        else:
            img = ""
        card_html = f'''<div class="col-md-4 mb-4"><div class="card h-100">{img}<div class="card-body"><h5 class="card-title">{c["name"]}</h5><p class="card-text">{c["description"]}</p><a href="./{c["slug"]}.html" class="stretched-link">View</a></div></div></div>'''
        cards_html.append(card_html)

    index_extra = '<div class="container"><div class="row">' + '\n'.join(cards_html) + '</div></div>'

    # render index page using template; pass media_prefix appropriate for
    # the restaurants index location
    index_rendered = skeleton.render(item={"name":"Restaurants Index","description":""}, page_title="Restaurants", banner_html="", logo_url="", extra_content=index_extra, media_prefix=index_media_prefix, site_prefix=index_site_prefix)
    index_file = rest_out / "index.html"
    index_file.write_text(index_rendered, encoding="utf-8")
    print(f"Wrote {index_file}")

    # Do homepage if provided
    if homepage_src.exists():
        try:
            homepage = load_jsonc(homepage_src)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSONC file {homepage_src}: {e}")
            raise SystemExit(1)
        
        if not isinstance(homepage, dict):
            print(f"Invalid homepage data in {homepage_src}")
            raise SystemExit(1)

        # render homepage into outdir/index.html
        # homepage lives at the output root so media paths should be referenced
        # directly (no "../" prefix).
        homepage_media_prefix = ""
        homepage_site_prefix = ""
        homepage_banner = build_banner_html(homepage, homepage_media_prefix, placeholder_if_missing=False)
        homepage_logo = choose_image(homepage, "local_logo_path", "remote_logo_url") or ""
        homepage_rendered = skeleton.render(item=homepage, page_title=homepage.get("title") or homepage.get("name"), banner_html=homepage_banner, logo_url=homepage_logo, extra_content=homepage.get("extra_content",""), media_prefix=homepage_media_prefix, site_prefix=homepage_site_prefix)
        homepage_file = outdir / "index.html"
        homepage_file.write_text(homepage_rendered, encoding="utf-8")
        print(f"Wrote {homepage_file}")
    else:
        print(f"No homepage file found at {homepage_src}; skipping homepage generation.")


if __name__ == "__main__":
    main()
