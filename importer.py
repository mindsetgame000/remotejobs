"""Collects jobs from Greenhouse, Lever, Ashby, a Google Sheet (CSV) and jobs.json.

Every job keeps the employer's real data: company name, location, job type and
the employer's own application link. Fields the source does not provide are left
empty instead of guessed.
"""
import csv, html, io, json, os, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser

UA = {"User-Agent": "RemoteJobsHub/1.0 (+job board importer)"}
FIXTURES = os.environ.get("JOB_FIXTURES")  # folder with saved API replies, for offline testing

COUNTRIES = """Afghanistan Albania Algeria Argentina Armenia Australia Austria Azerbaijan Bahrain Bangladesh
Belarus Belgium Bolivia Bosnia_and_Herzegovina Brazil Bulgaria Cambodia Cameroon Canada Chile China Colombia
Costa_Rica Croatia Cyprus Czech_Republic Czechia Denmark Dominican_Republic Ecuador Egypt El_Salvador Estonia
Ethiopia Finland France Georgia Germany Ghana Greece Guatemala Honduras Hong_Kong Hungary Iceland India Indonesia
Ireland Israel Italy Jamaica Japan Jordan Kazakhstan Kenya Kosovo Kuwait Latvia Lebanon Lithuania Luxembourg
Malaysia Malta Mexico Moldova Montenegro Morocco Nepal Netherlands New_Zealand Nicaragua Nigeria North_Macedonia
Norway Oman Pakistan Panama Paraguay Peru Philippines Poland Portugal Puerto_Rico Qatar Romania Rwanda
Saudi_Arabia Senegal Serbia Singapore Slovakia Slovenia South_Africa South_Korea Spain Sri_Lanka Sweden
Switzerland Taiwan Tanzania Thailand Tunisia Turkey Uganda Ukraine United_Arab_Emirates United_Kingdom
United_States Uruguay Uzbekistan Venezuela Vietnam Zambia Zimbabwe""".split()
COUNTRIES = {c.replace("_", " ").lower(): c.replace("_", " ") for c in COUNTRIES}
ALIASES = {"usa": "United States", "us": "United States", "u.s.": "United States", "united states of america": "United States",
           "uk": "United Kingdom", "u.k.": "United Kingdom", "england": "United Kingdom", "great britain": "United Kingdom",
           "uae": "United Arab Emirates", "korea": "South Korea", "republic of korea": "South Korea", "türkiye": "Turkey"}
ISO2 = {"US": "United States", "GB": "United Kingdom", "UK": "United Kingdom", "CA": "Canada", "DE": "Germany",
        "FR": "France", "ES": "Spain", "IT": "Italy", "NL": "Netherlands", "IE": "Ireland", "PL": "Poland",
        "PT": "Portugal", "IN": "India", "AU": "Australia", "NZ": "New Zealand", "BR": "Brazil", "MX": "Mexico",
        "AR": "Argentina", "CO": "Colombia", "JP": "Japan", "SG": "Singapore", "PH": "Philippines", "SE": "Sweden",
        "DK": "Denmark", "NO": "Norway", "FI": "Finland", "CH": "Switzerland", "AT": "Austria", "BE": "Belgium",
        "IL": "Israel", "ZA": "South Africa", "NG": "Nigeria", "KE": "Kenya", "AE": "United Arab Emirates",
        "RO": "Romania", "CZ": "Czechia", "HU": "Hungary", "GR": "Greece", "UA": "Ukraine", "TR": "Turkey",
        "KR": "South Korea", "CL": "Chile", "PE": "Peru", "EG": "Egypt", "PK": "Pakistan", "BD": "Bangladesh",
        "VN": "Vietnam", "TH": "Thailand", "MY": "Malaysia", "ID": "Indonesia", "EE": "Estonia", "LT": "Lithuania",
        "LV": "Latvia", "HR": "Croatia", "RS": "Serbia", "BG": "Bulgaria", "SK": "Slovakia", "SI": "Slovenia"}


def country_name(s):
    s = (s or "").strip().strip(".").lower()
    return COUNTRIES.get(s) or ALIASES.get(s)


def countries_in(text):
    """Country names that appear in a location string, e.g. 'Remote, Canada; Remote, United States'."""
    found = []
    for part in re.split(r"[;|/]| or |\band\b", text or ""):
        for piece in re.split(r"[,\-–()]", part):
            c = country_name(piece)
            if c and c not in found:
                found.append(c)
    return found


# ------------------------------------------------------------------ HTML cleaning
ALLOWED = {"p", "br", "ul", "ol", "li", "strong", "b", "em", "i", "h2", "h3", "h4"}
RENAME = {"h1": "h2", "h5": "h4", "h6": "h4"}
DROP = {"script", "style", "iframe", "noscript", "svg", "form", "button", "img", "video", "object"}


class _Cleaner(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in DROP:
            self.skip += 1
            return
        tag = RENAME.get(tag, tag)
        if not self.skip and tag in ALLOWED:
            self.out.append("<br>" if tag == "br" else f"<{tag}>")
        elif not self.skip and tag in ("div", "section"):
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in DROP:
            self.skip = max(0, self.skip - 1)
            return
        tag = RENAME.get(tag, tag)
        if not self.skip and tag in ALLOWED and tag != "br":
            self.out.append(f"</{tag}>")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(html.escape(data, quote=False))


def clean_html(raw):
    if not raw:
        return ""
    if "<" not in raw and "&lt;" not in raw:  # plain text
        parts = [p.strip() for p in re.split(r"\n\s*\n", raw) if p.strip()]
        return "".join("<p>" + html.escape(p).replace("\n", "<br>") + "</p>" for p in parts)
    if "&lt;" in raw and "<p" not in raw:
        raw = html.unescape(raw)
    c = _Cleaner()
    c.feed(raw)
    out = "".join(c.out)
    out = re.sub(r"<(p|li|h2|h3|h4|strong|b|em|i)>\s*</\1>", "", out)
    out = re.sub(r"(<br>\s*){3,}", "<br><br>", out)
    return out.strip()


def plain(raw, n=None):
    t = re.sub(r"<[^>]+>", " ", html.unescape(raw or ""))
    t = re.sub(r"\s+", " ", t).strip()
    return t[:n] if n else t


# ------------------------------------------------------------------ fetching
def get(url, kind="json"):
    if FIXTURES:
        name = re.sub(r"[^a-z0-9]+", "_", url.lower())[:150]
        path = os.path.join(FIXTURES, name)
        if not os.path.exists(path):
            raise FileNotFoundError(url)
        data = open(path, encoding="utf-8").read()
    else:
        last = None
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers=UA)
                with urllib.request.urlopen(req, timeout=40) as r:
                    data = r.read().decode("utf-8", "replace")
                break
            except Exception as e:  # noqa
                last = e
                if getattr(e, "code", 0) == 404:
                    raise
                time.sleep(2 * (attempt + 1))
        else:
            raise last
    return json.loads(data) if kind == "json" else data


def type_from_text(t):
    t = (t or "").lower()
    if re.search(r"part[\s-]?time", t): return "PART_TIME"
    if re.search(r"intern", t): return "INTERN"
    if re.search(r"contract|freelance|contractor", t): return "CONTRACTOR"
    if re.search(r"temporary|seasonal|temp\b", t): return "TEMPORARY"
    if re.search(r"full[\s-]?time", t): return "FULL_TIME"
    return ""


def iso_date(v):
    if not v:
        return ""
    if isinstance(v, (int, float)):
        return time.strftime("%Y-%m-%d", time.gmtime(v / 1000 if v > 1e11 else v))
    return str(v)[:10]


# ------------------------------------------------------------------ sources
def from_greenhouse(board):
    data = get(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true")
    out = []
    for j in data.get("jobs", []):
        loc = (j.get("location") or {}).get("name", "")
        if "remote" not in loc.lower():
            continue
        out.append({
            "id": f"gh-{j.get('id')}", "title": (j.get("title") or "").strip(),
            "company": j.get("company_name") or board.replace("-", " ").title(),
            "company_url": "", "location_text": loc, "remote": True,
            "applicant_countries": countries_in(loc),
            "employment_type": type_from_text(j.get("title")),
            "department": ", ".join(d.get("name", "") for d in j.get("departments", []) if d.get("name")),
            "description": clean_html(j.get("content", "")),
            "apply_url": j.get("absolute_url", ""),
            "date_posted": iso_date(j.get("first_published") or j.get("updated_at")),
            "source": "greenhouse",
        })
    return out


def from_lever(company):
    data = get(f"https://api.lever.co/v0/postings/{company}?mode=json")
    commit = {"full-time": "FULL_TIME", "full time": "FULL_TIME", "part-time": "PART_TIME", "part time": "PART_TIME",
              "contract": "CONTRACTOR", "contractor": "CONTRACTOR", "intern": "INTERN", "internship": "INTERN",
              "temporary": "TEMPORARY"}
    out = []
    for j in data if isinstance(data, list) else []:
        cats = j.get("categories") or {}
        loc = cats.get("location") or ""
        all_locs = "; ".join(cats.get("allLocations") or []) or loc
        if (j.get("workplaceType") or "").lower() != "remote" and "remote" not in all_locs.lower():
            continue
        countries = countries_in(all_locs)
        if not countries and j.get("country"):
            c = ISO2.get(j["country"].upper())
            if c: countries = [c]
        desc = j.get("description") or ""
        for lst in j.get("lists") or []:
            desc += f"<h3>{html.escape(lst.get('text', ''))}</h3>" + (lst.get("content") or "")
        desc += j.get("additional") or ""
        sal = j.get("salaryRange") or {}
        unit = {"per-year-salary": "YEAR", "per-month-salary": "MONTH", "per-hour-wage": "HOUR"}.get(sal.get("interval", ""), "")
        name = j.get("hostedUrl", "").split("/")[3] if j.get("hostedUrl") else company
        out.append({
            "id": f"lv-{j.get('id')}", "title": (j.get("text") or "").strip(),
            "company": name.replace("-", " ").title(), "company_url": "",
            "location_text": all_locs or "Remote", "remote": True, "applicant_countries": countries,
            "employment_type": commit.get((cats.get("commitment") or "").lower(), type_from_text(j.get("text"))),
            "department": cats.get("department") or cats.get("team") or "",
            "description": clean_html(desc),
            "apply_url": j.get("hostedUrl") or j.get("applyUrl") or "",
            "date_posted": iso_date(j.get("createdAt")),
            "salary_min": sal.get("min") or "", "salary_max": sal.get("max") or "",
            "salary_currency": sal.get("currency") or "", "salary_unit": unit if sal else "",
            "source": "lever",
        })
    return out


def from_ashby(org):
    data = get(f"https://api.ashbyhq.com/posting-api/job-board/{org}?includeCompensation=true")
    types = {"FullTime": "FULL_TIME", "PartTime": "PART_TIME", "Contract": "CONTRACTOR",
             "Intern": "INTERN", "Temporary": "TEMPORARY"}
    out = []
    for j in data.get("jobs", []):
        if not j.get("isListed", True):
            continue
        locs = [j.get("location") or ""] + [s.get("location", "") for s in j.get("secondaryLocations") or []]
        loc_text = "; ".join(l for l in locs if l)
        if not j.get("isRemote") and "remote" not in loc_text.lower():
            continue
        countries = countries_in(loc_text)
        addr = (((j.get("address") or {}).get("postalAddress")) or {}).get("addressCountry")
        if not countries and addr:
            c = country_name(addr) or ISO2.get(str(addr).upper())
            if c: countries = [c]
        out.append({
            "id": f"ab-{j.get('id')}", "title": (j.get("title") or "").strip(),
            "company": org.replace("-", " ").title(), "company_url": "",
            "location_text": loc_text or "Remote", "remote": True, "applicant_countries": countries,
            "employment_type": types.get(j.get("employmentType", ""), ""),
            "department": j.get("department") or j.get("team") or "",
            "description": clean_html(j.get("descriptionHtml") or j.get("descriptionPlain") or ""),
            "apply_url": j.get("jobUrl") or j.get("applyUrl") or "",
            "date_posted": iso_date(j.get("publishedAt")),
            "source": "ashby",
        })
    return out


def truthy(v):
    return str(v).strip().lower() in ("1", "yes", "y", "true", "remote")


def normalize_manual(r, idx, source):
    countries = r.get("applicant_countries") or r.get("countries") or ""
    if isinstance(countries, str):
        countries = [country_name(c) or c.strip() for c in countries.split(",") if c.strip()]
    title = (r.get("title") or "").strip()
    return {
        "id": str(r.get("id") or f"{source}-{idx}-{re.sub(r'[^a-z0-9]+', '-', title.lower())[:40]}"),
        "title": title, "company": (r.get("company") or "").strip(),
        "company_url": r.get("company_url") or "",
        "location_text": r.get("location") or ("Remote" if truthy(r.get("remote", "yes")) else ""),
        "remote": truthy(r.get("remote", "yes")), "applicant_countries": countries,
        "city": r.get("city") or "", "country": r.get("country") or "",
        "employment_type": (r.get("employment_type") or "").strip().upper().replace("-", "_").replace(" ", "_"),
        "department": r.get("category") or "",
        "description": clean_html(r.get("description") or ""),
        "apply_url": (r.get("apply_url") or "").strip(),
        "date_posted": iso_date(r.get("date_posted")) or time.strftime("%Y-%m-%d"),
        "valid_through": iso_date(r.get("valid_through")),
        "salary_min": r.get("salary_min") or "", "salary_max": r.get("salary_max") or "",
        "salary_currency": r.get("salary_currency") or "", "salary_unit": (r.get("salary_unit") or "").upper(),
        "source": source, "featured": True,
    }


def from_sheet(url):
    text = get(url, kind="text")
    rows = list(csv.DictReader(io.StringIO(text)))
    rows = [{(k or "").strip().lower(): (v or "").strip() for k, v in r.items()} for r in rows]
    return [normalize_manual(r, i, "sheet") for i, r in enumerate(rows) if r.get("title") and r.get("apply_url")]


def from_json(path):
    if not os.path.exists(path):
        return []
    rows = json.load(open(path, encoding="utf-8"))
    return [normalize_manual(r, i, "manual") for i, r in enumerate(rows) if r.get("title") and r.get("apply_url")]


def collect(companies_file="companies.json", jobs_file="jobs.json", sheet_url=""):
    cfg = json.load(open(companies_file, encoding="utf-8"))
    tasks = [(from_greenhouse, b) for b in cfg.get("greenhouse", [])]
    tasks += [(from_lever, c) for c in cfg.get("lever", [])]
    tasks += [(from_ashby, o) for o in cfg.get("ashby", [])]
    jobs, report = [], []

    def run(t):
        fn, name = t
        try:
            res = fn(name)
            return name, fn.__name__[5:], res, None
        except Exception as e:  # noqa
            return name, fn.__name__[5:], [], e

    with ThreadPoolExecutor(max_workers=8) as ex:
        for name, src, res, err in ex.map(run, tasks):
            report.append(f"  {src:10} {name:22} {'SKIPPED (' + type(err).__name__ + ')' if err else str(len(res)) + ' remote jobs'}")
            jobs += res
    if sheet_url:
        try:
            s = from_sheet(sheet_url)
            report.append(f"  sheet      {'Google Sheet':22} {len(s)} jobs")
            jobs += s
        except Exception as e:  # noqa
            report.append(f"  sheet      Google Sheet           SKIPPED ({type(e).__name__})")
    m = from_json(jobs_file)
    report.append(f"  manual     {'jobs.json':22} {len(m)} jobs")
    jobs += m
    print("Job sources:\n" + "\n".join(report), file=sys.stderr)
    return [j for j in jobs if j["title"] and j["apply_url"].startswith(("http://", "https://"))]
