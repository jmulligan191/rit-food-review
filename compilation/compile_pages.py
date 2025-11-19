
#!/usr/bin/env python3
"""Jinja-only compiler (final version).

This file intentionally contains only the Jinja2-based compiler and writes
rendered pages directly to the output folder (default `restaurants/`).
"""
import argparse
import json
from pathlib import Path
import json5

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


def build_banner_html(item: dict) -> str:
    banner = choose_image(item, "local_banner_path", "remote_banner_url")
    if not banner:
        return ""
    return f'<div class="banner"><img src="{banner}" alt="{item.get("name","")} banner" class="img-fluid w-100"/></div>'

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

    # create specific restaurant pages, collect summary for index
    cards = []
    try:
        from jinja2 import Environment, select_autoescape
    except Exception:
        print("jinja2 is required. Install with: pip install jinja2")
        raise SystemExit(1)

    tpl_text = template_path.read_text(encoding="utf-8")
    env = Environment(autoescape=select_autoescape(["html", "xml"]))
    jtpl = env.from_string(tpl_text)

    if not data or not isinstance(data, dict):
        print(f"Invalid or no restaurant data found in {restaurants_src}")
        raise SystemExit(1)

    for key, item in data.items():
        slug = item.get("slug") or key
        filename = rest_out / f"{slug}.html"
        banner_html = build_banner_html(item)
        logo_url = choose_image(item, "local_logo_path", "remote_logo_url") or ""
        rendered = jtpl.render(item=item, page_title=item.get("name"), banner_html=banner_html, logo_url=logo_url, extra_content="")
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
    for c in cards:
        img = f'<img src="{c["logo"]}" class="card-img-top" alt="{c["name"]} logo">' if c["logo"] else ""
        card_html = f'''<div class="col-md-4 mb-4"><div class="card h-100">{img}<div class="card-body"><h5 class="card-title">{c["name"]}</h5><p class="card-text">{c["description"]}</p><a href="./{c["slug"]}.html" class="stretched-link">View</a></div></div></div>'''
        cards_html.append(card_html)

    index_extra = '<div class="container"><div class="row">' + '\n'.join(cards_html) + '</div></div>'

    # render index page using template
    index_rendered = jtpl.render(item={"name":"Restaurants Index","description":"All restaurants"}, page_title="Restaurants", banner_html="", logo_url="", extra_content=index_extra)
    index_file = rest_out / "index.html"
    index_file.write_text(index_rendered, encoding="utf-8")
    print(f"Wrote {index_file}")

    # Do homepage if provided
    if homepage_src.exists():
        homepage = load_jsonc(homepage_src)
        # render homepage into outdir/index.html
        homepage_banner = build_banner_html(homepage)
        homepage_logo = choose_image(homepage, "local_logo_path", "remote_logo_url") or ""
        homepage_rendered = jtpl.render(item=homepage, page_title=homepage.get("title") or homepage.get("name"), banner_html=homepage_banner, logo_url=homepage_logo, extra_content=homepage.get("extra_content",""))
        homepage_file = outdir / "index.html"
        homepage_file.write_text(homepage_rendered, encoding="utf-8")
        print(f"Wrote {homepage_file}")
    else:
        print(f"No homepage file found at {homepage_src}; skipping homepage generation.")


if __name__ == "__main__":
    main()
