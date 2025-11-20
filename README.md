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
 - **Format**: Files are JSONC (JSON with comments allowed). Each restaurant entry is an object keyed by a slug with fields such as `slug`, `name`, `description`, `hours`, `contact`, `local_logo_path`, `remote_logo_url`, `local_banner_path`, and `remote_banner_url`.
 - **New fields**: Two new metadata fields are supported per entry:
	 - `created_by`: string — name of the person who created the entry (e.g. "John Mulligan" or "Evan Vaagen").
	 - `edited_by`: array of strings — people who edited the entry (the compiler displays these as a comma-separated list). Each string should be on its own line in the JSONC for readability.
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
- **Example (Review entry):**
```jsonc
{
	"author": "John Doe", // name of the reviewer
	"author_image_url": "https://example.com/profiles/johndoe.jpg", // optional URL to the reviewer's profile image (or null)
	"date": "2024-10-01", // date of the review in YYYY-MM-DD format
	"rating": 4, // rating out of 5 (stars?)
	"description": "Great variety of food options and accommodating to dietary needs. The pizza station is a favorite!", // content of the review
	"attachment_url": null, // optional URL to an image related to the review, shows alongside the review if present (or null)

	"upvotes": 12, // number of upvotes the review has received
	"downvotes": 2 // number of downvotes the review has received
},
```

## Compilation / Build
- **Purpose**: A Python script reads the JSONC files and compiles them into final HTML pages using Jinja templates. Generated pages are written into the `docs/` folder (for example `docs/restaurants/{slug}.html` and `docs/index.html`).
    - The reason I don't use a folder like `src/` is that GitHub Pages serves from `docs/` and won't let you serve it anywhere else but the root. Gracias Github Pages.
- **Script location**: The compiler is `compilation/compile_pages.py`.
- **Default inputs/outputs:**
	- **Restaurants input:** `restaurants.jsonc` (default) — you can pass another file with `--restaurants`.
	- **Homepage input:** `homepage.jsonc` (default) — optional; if present the script will generate `docs/index.html`.
	- **Template:** `templates/skeleton.html` (default) — can be changed with `--template`.
	- **Output directory:** `docs/` (default) — use `--out` to change.

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
python3 compilation/compile_pages.py --restaurants restaurants.jsonc --homepage homepage.jsonc --template templates/skeleton.html --out docs
```
- **From there, you should be able to view the generated HTML files in the `docs/` directory using a web browser.**

# Notes & tips
- **Overwriting:** Generated files will overwrite existing files in the `docs/` output directory.
- **Adding restaurants:** Add new entries to your restaurants JSONC (e.g., `restaurants.jsonc`) following the example structure and re-run the compiler.
 - **Adding restaurants:** Add new entries to your restaurants JSONC (e.g., `restaurants.jsonc`) following the example structure and re-run the compiler. Include `created_by` and `edited_by` if you want that metadata displayed on the compiled page.
- **Template changes:** Edit `templates/skeleton.html` to change the look of all compiled pages.

