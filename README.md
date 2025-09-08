# Attorney Bio Scraper (Conference Edition)

Scrape attorney biography pages to surface conference-friendly talking points:
education, hobbies, pets, family mentions, community involvement, etc.

## Features
- CSV input of URLs + target names (handles multi-attorney pages)
- Finds the block of content around the target attorney’s name
- Extracts likely schools, hobbies, pets, family, community keywords
- CLI flags for input/output paths
- Progress bar + simple logs

## Quickstart

```bash
git clone <your-repo-url>
cd attorney-bio-scraper
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
