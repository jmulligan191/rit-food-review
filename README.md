# the best food review site at RIT
Welcome to the RIT Food Review site! This website provides comprehensive reviews and information about various dining
options available at the Rochester Institute of Technology (RIT). Whether you're a student, faculty member, or visitor,
this site aims to help you make informed decisions about where to eat on campus.

## Made by the following people:
- [John Mulligan](https://github.com/jmulligan191)
- [Colin He](https://github.com/ColinGHe)
- [Evan Vaagen](https://github.com/wisoven)
- [Hansen Rapp](https://github.com/Untitled-dog)

# How the project works

## Data Source
- **Location**: The compilation inputs are JSON/JSONC files stored under `compilation/static` (or other JSONC files at the repo root such as `restaurants.jsonc` and `homepage.jsonc`).
- **Format**: Files are JSONC (JSON with comments allowed). Each restaurant entry is an object keyed by a slug with fields such as `slug`, `name`, `description`, `hours`, `contact`, `local_logo_path`, `remote_logo_url`, `local_banner_path`, and `remote_banner_url`.
- **Example (restaurant entry):**
```jsonc
"gracies": {
	"slug": "gracies",
	"name": "Gracies",
	"description": "RIT's largest dining hall...",
	"hours": { "monday": "7:00AM-7:30PM", "tuesday": "7:00AM-7:30PM" },
	"contact": { "phone": "(585) 475-2411", "email": null },
	"local_logo_path": "media/gracies_logo.png",
	"local_banner_path": "media/gracies_banner.png"
}
```

## Compilation / Build
- **Purpose**: A Python script reads the JSONC files and compiles them into final HTML pages using Jinja templates. Generated pages are written into the `src/` folder (for example `src/restaurants/{slug}.html` and `src/index.html`).
- **Script location**: The compiler is `compilation/compile_pages.py`.
- **Default inputs/outputs:**
	- **Restaurants input:** `restaurants.jsonc` (default) — you can pass another file with `--restaurants`.
	- **Homepage input:** `homepage.jsonc` (default) — optional; if present the script will generate `src/index.html`.
	- **Template:** `templates/skeleton.html` (default) — can be changed with `--template`.
	- **Output directory:** `src/` (default) — use `--out` to change.

# How to run locally
- **Clone the repository:**
```bash
git clone https://github.com/jmulligan191/rit-food-review.git
cd rit-food-review
```
- **Create a virtual environment (optional but recommended):**
```bash
# Python3 points to where you have python3 installed (may be py if you are on Windows)
python3 -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

- **Install dependencies:**
```bash
python3 -m pip install -r requirements.txt
```
- **Run the compiler (defaults):**
```bash
python3 compilation/compile_pages.py
```
- **Run with explicit files or output directory:**
```bash
python3 compilation/compile_pages.py --restaurants restaurants.jsonc --homepage homepage.jsonc --template templates/skeleton.html --out src
```
- **From there, you should be able to view the generated HTML files in the `src/` directory using a web browser.**

# Notes & tips
- **Overwriting:** Generated files will overwrite existing files in the `src/` output directory.
- **Adding restaurants:** Add new entries to your restaurants JSONC (e.g., `restaurants.jsonc`) following the example structure and re-run the compiler.
- **Template changes:** Edit `templates/skeleton.html` to change the look of all compiled pages.

