# Remote Jobs Hub

Static remote job board for Cloudflare Pages. Jobs are imported on every build from:

- `companies.json` – Greenhouse, Lever and Ashby job boards (remote jobs only)
- a Google Sheet published as CSV (set `SHEET_CSV_URL` in Cloudflare > Settings > Variables)
- `jobs.json` – jobs you add by hand

Cloudflare Pages settings: build command `python3 build.py`, output directory `site`,
environment variable `SITE_URL` = your address (e.g. `https://us.remotejobs.loveslife.biz`).

Daily updates: create a Deploy Hook in Cloudflare Pages and save it as the GitHub secret `CF_DEPLOY_HOOK`.

Ads: paste Adsterra codes into `static/ads/*.html` and the Social Bar address into `static/assets/ads.js`.

Google Sheet columns: title, company, company_url, category, employment_type, remote, applicant_countries,
salary_min, salary_max, salary_currency, salary_unit, description, apply_url, date_posted, valid_through
