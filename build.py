#!/usr/bin/env python3
"""Builds the whole Remote Jobs Hub site into ./site/ (Cloudflare Pages build command: python3 build.py)."""
import datetime, hashlib, html, json, os, re, shutil, sys
from importer import collect, plain
from blog_posts import POSTS

# ======================== SETTINGS (edit these) ========================
BASE = os.environ.get("SITE_URL", "https://us.remotejobs.loveslife.biz").rstrip("/")
BRAND = "Remote Jobs Hub"
EMAIL = "your-email@example.com"
# Google Sheet: File > Share > Publish to web > CSV, paste the link here (or set SHEET_CSV_URL in Cloudflare).
SHEET_CSV_URL = os.environ.get("SHEET_CSV_URL", "")
MAX_JOBS = 12000          # Cloudflare Pages free plan allows 20,000 files per site
VALID_DAYS = 45           # a job leaves the site this many days after it was posted
PER_PAGE = 30
APPLY_WAIT_SECONDS = 5
# ======================================================================

OUT = "site"
TODAY = datetime.date.today()
esc = lambda s: html.escape(str(s or ""), quote=True)

CATEGORIES = [
    ("remote-customer-service-jobs", "Remote Customer Service Jobs", "Customer Service",
     r"customer|support|service|success|help ?desk|call cent|chat agent|client care|experience specialist",
     "Remote customer service jobs let you help customers by chat, email or phone from home. Common titles include support specialist, customer success manager and help desk agent."),
    ("remote-data-entry-jobs", "Remote Data Entry & Admin Jobs", "Data Entry & Admin",
     r"data entry|admin|assistant|clerk|coordinator|operations associate|typist|transcri|annotat",
     "Real remote data entry jobs are less common than ads suggest, so this page also shows close matches such as admin assistant, coordinator and operations roles. Real employers never ask you to pay to start."),
    ("remote-software-development-jobs", "Remote Software Development Jobs", "Software Development",
     r"software|developer|engineer|frontend|front-end|backend|back-end|full ?stack|devops|programmer|\bsre\b|mobile|ios|android|architect",
     "Remote software development jobs cover frontend, backend, full-stack, mobile, infrastructure and DevOps roles at companies that hire across time zones."),
    ("remote-data-analytics-jobs", "Remote Data & Analytics Jobs", "Data & Analytics",
     r"data scien|data analy|analytics|business intelligence|\bbi\b|machine learning|\bml\b|\bai\b|statistic",
     "Remote data and analytics jobs include data analyst, data scientist, analytics engineer and machine learning roles."),
    ("remote-product-project-management-jobs", "Remote Product & Project Management Jobs", "Product & Project",
     r"product manag|project manag|program manag|product owner|scrum|delivery manag",
     "Remote product and project management jobs: product managers, project and program managers, and delivery leads."),
    ("remote-marketing-jobs", "Remote Marketing Jobs", "Marketing",
     r"marketing|seo|growth|social media|paid media|brand|community|content strateg|communications|\bpr\b",
     "Remote marketing jobs span SEO, paid ads, social media, content, brand and growth roles."),
    ("remote-sales-jobs", "Remote Sales Jobs", "Sales",
     r"sales|account executive|account manager|business development|\bsdr\b|\bbdr\b|partnership",
     "Remote sales jobs include sales development (SDR/BDR), account executive, account management and partnerships roles."),
    ("remote-design-jobs", "Remote Design Jobs", "Design",
     r"design|\bux\b|\bui\b|illustrat|creative|visual|motion|research(er)?\b",
     "Remote design jobs include product (UI/UX), brand, visual, motion and research roles. A clean online portfolio matters most."),
    ("remote-writing-jobs", "Remote Writing & Content Jobs", "Writing",
     r"writ|editor|copy|technical writer|proofread|documentation|content (designer|creator|manager)",
     "Remote writing jobs include copywriting, technical writing, documentation, editing and content roles."),
    ("remote-finance-accounting-jobs", "Remote Finance & Accounting Jobs", "Finance",
     r"financ|accountant|accounting|payroll|tax|audit|controller|treasury|\bfp&a\b|bookkeep|billing",
     "Remote finance and accounting jobs: accountants, financial analysts, payroll, tax and FP&A roles."),
    ("remote-hr-recruiting-jobs", "Remote HR & Recruiting Jobs", "HR & Recruiting",
     r"recruit|talent|sourcer|human resources|\bhr\b|people (ops|partner|operations)|people business",
     "Remote HR and recruiting jobs: recruiters, sourcers, HR business partners and people operations."),
    ("remote-it-security-jobs", "Remote IT & Security Jobs", "IT & Security",
     r"security|\bit\b|it support|systems admin|sysadmin|network|cloud|infrastructure|compliance",
     "Remote IT and security jobs: IT support, security engineers, cloud and infrastructure, and compliance roles."),
]
CAT_RE = [(slug, re.compile(rx, re.I)) for slug, _, _, rx, _ in CATEGORIES]
TYPE_LABEL = {"FULL_TIME": "Full-time", "PART_TIME": "Part-time", "CONTRACTOR": "Contract",
              "TEMPORARY": "Temporary", "INTERN": "Internship", "PER_DIEM": "Per diem", "OTHER": "Other"}


# ------------------------------------------------------------------ job prep
def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:70].strip("-")


def prepare(jobs):
    seen, out = set(), []
    for j in jobs:
        if not j.get("date_posted"):
            j["date_posted"] = TODAY.isoformat()
        try:
            posted = datetime.date.fromisoformat(j["date_posted"])
        except ValueError:
            posted = TODAY
            j["date_posted"] = TODAY.isoformat()
        if posted > TODAY:
            posted, j["date_posted"] = TODAY, TODAY.isoformat()
        vt = j.get("valid_through") or (posted + datetime.timedelta(days=VALID_DAYS)).isoformat()
        if vt < TODAY.isoformat():
            continue  # expired
        j["valid_through"] = vt
        key = (j["title"].lower(), j["company"].lower(), j["apply_url"])
        if key in seen:
            continue
        seen.add(key)
        short = hashlib.md5(j["id"].encode()).hexdigest()[:6]
        j["slug"] = f"{slugify(j['title'] + ' ' + j['company'])}-{short}"
        text = f"{j['title']} {j.get('department', '')}"
        j["cats"] = [slug for slug, rx in CAT_RE if rx.search(text)]
        out.append(j)
    out.sort(key=lambda j: (not j.get("featured"), j["date_posted"]), reverse=False)
    out.sort(key=lambda j: j["date_posted"], reverse=True)
    out.sort(key=lambda j: not j.get("featured"))
    return out[:MAX_JOBS]


def salary_label(j):
    lo, hi = j.get("salary_min"), j.get("salary_max")
    if not lo and not hi:
        return ""
    cur = j.get("salary_currency") or "USD"
    sym = "$" if cur == "USD" else cur + " "
    f = lambda v: sym + f"{float(v):,.0f}"
    unit = {"HOUR": "/hour", "DAY": "/day", "WEEK": "/week", "MONTH": "/month", "YEAR": "/year"}.get(j.get("salary_unit") or "", "")
    return (f"{f(lo)} - {f(hi)}" if lo and hi else f(lo or hi)) + unit


def location_label(j):
    if j.get("remote"):
        c = j.get("applicant_countries") or []
        if c:
            return "Remote · " + ", ".join(c[:3]) + (f" +{len(c) - 3}" if len(c) > 3 else "")
        lt = (j.get("location_text") or "").strip()
        return lt if lt and len(lt) < 60 else "Remote"
    return ", ".join(x for x in [j.get("city"), j.get("country")] if x) or (j.get("location_text") or "")


def job_schema(j):
    """Structured data only from real fields. Missing required data -> no schema."""
    if not j["company"] or not j["description"]:
        return None
    s = {
        "@context": "https://schema.org", "@type": "JobPosting",
        "title": j["title"], "description": j["description"],
        "datePosted": j["date_posted"], "validThrough": j["valid_through"] + "T23:59:59",
        "hiringOrganization": {"@type": "Organization", "name": j["company"]},
        "directApply": False,
    }
    if j.get("company_url"):
        s["hiringOrganization"]["sameAs"] = j["company_url"]
    if j.get("employment_type") in TYPE_LABEL:
        s["employmentType"] = j["employment_type"]
    if j.get("remote"):
        if not j.get("applicant_countries"):
            return None
        s["jobLocationType"] = "TELECOMMUTE"
        s["applicantLocationRequirements"] = [{"@type": "Country", "name": c} for c in j["applicant_countries"]]
    else:
        if not j.get("country"):
            return None
        s["jobLocation"] = {"@type": "Place", "address": {k: v for k, v in {
            "@type": "PostalAddress", "addressLocality": j.get("city"), "addressCountry": j.get("country")}.items() if v}}
    if j.get("salary_min") or j.get("salary_max"):
        v = {"@type": "QuantitativeValue", "unitText": j.get("salary_unit") or "YEAR"}
        if j.get("salary_min"): v["minValue"] = float(j["salary_min"])
        if j.get("salary_max"): v["maxValue"] = float(j["salary_max"])
        s["baseSalary"] = {"@type": "MonetaryAmount", "currency": j.get("salary_currency") or "USD", "value": v}
    return s


# ------------------------------------------------------------------ layout
AD_LEADER = ('<div class="ad ad-wide"><iframe src="/ads/banner-728x90.html" width="728" height="90" loading="lazy" scrolling="no" title="Advertisement"></iframe></div>'
             '<div class="ad ad-narrow"><iframe src="/ads/banner-320x50.html" width="320" height="50" loading="lazy" scrolling="no" title="Advertisement"></iframe></div>')
AD_BOX = '<div class="ad"><iframe src="/ads/banner-300x250.html" width="300" height="250" loading="lazy" scrolling="no" title="Advertisement"></iframe></div>'


def nav():
    return f"""<header class="topbar"><div class="wrap topbar-in">
<a href="/" class="logo">{BRAND}</a>
<nav class="menu" aria-label="Main"><a href="/jobs/">Jobs</a><a href="/#categories">Categories</a><a href="/blog/">Blog</a><a href="/post-a-job/" class="btn-accent">Post a Job</a></nav>
</div></header>"""


def footer():
    cats = "".join(f'<li><a href="/{c[0]}/">{c[1]}</a></li>' for c in CATEGORIES[:8])
    posts = "".join(f'<li><a href="/blog/{p["slug"]}/">{p["title"]}</a></li>' for p in POSTS)
    return f"""<footer class="footer"><div class="wrap footer-grid">
<div><p class="logo">{BRAND}</p><p class="muted-light">Remote jobs from employers' own career pages, updated every day. Every application happens on the employer's site.</p></div>
<div><h3>Browse Jobs</h3><ul>{cats}<li><a href="/jobs/">All remote jobs</a></li></ul></div>
<div><h3>From the Blog</h3><ul>{posts}</ul></div>
<div><h3>Site</h3><ul><li><a href="/about/">About</a></li><li><a href="/contact/">Contact</a></li><li><a href="/privacy-policy/">Privacy Policy</a></li><li><a href="/post-a-job/">Post a Job</a></li></ul></div>
</div><div class="wrap footer-bottom">&copy; {TODAY.year} {BRAND}.</div></footer>"""


NAV, FOOT = None, None
FILES = 0


def write(path, body, title, desc, schemas=(), robots="index, follow", canonical=True, extra_head=""):
    global FILES
    url = BASE + path
    sch = "".join('<script type="application/ld+json">' + json.dumps(s, ensure_ascii=False).replace("</", "<\\/") + "</script>"
                  for s in schemas if s)
    page = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="robots" content="{robots}">
{f'<link rel="canonical" href="{esc(url)}">' if canonical else ''}
<meta property="og:type" content="website"><meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{esc(url)}">
<meta property="og:site_name" content="{esc(BRAND)}"><meta name="twitter:card" content="summary">
<link rel="stylesheet" href="/assets/style.css">{extra_head}{sch}
</head><body>
{NAV}
<main>{body}</main>
{FOOT}
<script src="/assets/app.js" defer></script><script src="/assets/ads.js" defer></script>
</body></html>"""
    if path.endswith(".html"):
        fp = os.path.join(OUT, path.lstrip("/"))
    else:
        fp = os.path.join(OUT, path.strip("/"), "index.html")
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    with open(fp, "w", encoding="utf-8") as f:
        f.write(page)
    FILES += 1


def crumbs(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": BASE + u} for i, (n, u) in enumerate(items)]}


def ago(d):
    days = (TODAY - datetime.date.fromisoformat(d)).days
    return "Today" if days <= 0 else ("1 day ago" if days == 1 else (f"{days} days ago" if days < 30 else d))


def card(j):
    tags = '<span class="tag gold">Featured</span>' if j.get("featured") else ""
    tags += f'<span class="tag green">{esc(location_label(j))}</span>'
    if j.get("employment_type") in TYPE_LABEL:
        tags += f'<span class="tag">{TYPE_LABEL[j["employment_type"]]}</span>'
    if salary_label(j):
        tags += f'<span class="tag">{esc(salary_label(j))}</span>'
    return (f'<a class="job" href="/job/{j["slug"]}/"><span class="ph">{esc(j["company"][:1].upper() or "?")}</span>'
            f'<div class="job-main"><div class="job-title">{esc(j["title"])}</div><div class="job-co">{esc(j["company"])}</div>'
            f'<div class="tags">{tags}</div></div><div class="job-side">{ago(j["date_posted"])}<br><span class="apply">View job &rarr;</span></div></a>')


def job_list(jobs):
    return '<div class="job-list">' + "".join(card(j) for j in jobs) + "</div>" if jobs else '<p class="muted">No openings right now. New jobs are added every day.</p>'


def pager(base, page, pages):
    if pages <= 1:
        return ""
    link = lambda p: base if p == 1 else f"{base}page/{p}/"
    prev = f'<a class="btn" href="{link(page - 1)}">&larr; Newer</a>' if page > 1 else "<span></span>"
    nxt = f'<a class="btn" href="{link(page + 1)}">Older &rarr;</a>' if page < pages else "<span></span>"
    return f'<div class="pager">{prev}<span class="muted">Page {page} of {pages}</span>{nxt}</div>'


def paged(base, jobs, title, desc, intro_html, crumb_name):
    pages = max(1, -(-len(jobs) // PER_PAGE))
    thin = len(jobs) < 3  # nearly empty pages stay out of Google until they fill up
    urls = []
    for p in range(1, pages + 1):
        path = base if p == 1 else f"{base}page/{p}/"
        chunk = jobs[(p - 1) * PER_PAGE: p * PER_PAGE]
        t = title + (f" – Page {p}" if p > 1 else "") + f" | {BRAND}"
        body = f"""<section class="hero hero-small"><div class="wrap">
<nav class="crumbs"><a href="/">Home</a> / {esc(crumb_name)}</nav><h1>{esc(title)}{f' <span class="muted">(page {p})</span>' if p > 1 else ''}</h1>
{intro_html if p == 1 else ''}</div></section>
{AD_LEADER}
<section class="wrap jobs"><p class="muted">{len(jobs):,} open remote jobs</p>{job_list(chunk)}{pager(base, p, pages)}</section>
{AD_BOX}"""
        write(path, body, t, desc, [crumbs([("Home", "/"), (crumb_name, base)])], robots="noindex, follow" if thin else "index, follow")
        if not thin:
            urls.append(path)
    return urls


# ------------------------------------------------------------------ build
def main():
    global NAV, FOOT
    NAV, FOOT = nav(), footer()
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    shutil.copytree("static", OUT)

    jobs = prepare(collect("companies.json", "jobs.json", SHEET_CSV_URL))
    print(f"{len(jobs)} live jobs after removing expired and duplicates", file=sys.stderr)
    urls = []

    # ---- job pages
    for i, j in enumerate(jobs):
        path = f"/job/{j['slug']}/"
        similar = [x for x in jobs if x is not j and set(x["cats"]) & set(j["cats"])][:6] or jobs[max(0, i - 3): i][:6]
        tags = f'<span class="tag green">{esc(location_label(j))}</span>'
        if j.get("employment_type") in TYPE_LABEL:
            tags += f'<span class="tag">{TYPE_LABEL[j["employment_type"]]}</span>'
        if salary_label(j):
            tags += f'<span class="tag">{esc(salary_label(j))}</span>'
        tags += f'<span class="tag">Posted {datetime.date.fromisoformat(j["date_posted"]).strftime("%b %d, %Y")}</span>'
        apply_href = f"/apply/?j={j['slug']}"
        cat_links = "".join(f'<a class="pill" href="/{c[0]}/">{c[2]}</a>' for c in CATEGORIES if c[0] in j["cats"])
        body = f"""{AD_LEADER}
<article class="wrap article job-page">
<nav class="crumbs"><a href="/">Home</a> / <a href="/jobs/">Jobs</a> / {esc(j['title'])}</nav>
<h1>{esc(j['title'])}</h1><p class="job-co big">{esc(j['company'])}</p>
<div class="tags">{tags}</div>
<div class="apply-top"><a class="btn-accent" href="{apply_href}" rel="nofollow">Apply for this job</a></div>
<div class="job-desc">{j['description'] or '<p>See the full description on the employer\'s application page.</p>'}</div>
{AD_BOX}
<div class="cta-box"><h2>Interested?</h2><p>You will apply on {esc(j['company'])}'s own application page.</p>
<a class="btn-accent" href="{apply_href}" rel="nofollow">Apply now</a></div>
{f'<div class="pills">{cat_links}</div>' if cat_links else ''}
<p class="muted">Never pay to apply for a job. <a href="/blog/how-to-spot-remote-job-scams/">How to spot job scams</a>.</p>
</article>
{f'<section class="wrap"><h2>Similar Remote Jobs</h2>{job_list(similar)}</section>' if similar else ''}"""
        desc = f"{j['title']} at {j['company']} ({location_label(j)}). " + plain(j["description"], 120)
        write(path, body, f"{j['title']} at {j['company']} | {BRAND}", desc[:158],
              [job_schema(j), crumbs([("Home", "/"), ("Jobs", "/jobs/"), (j["title"], path)])])
        urls.append(path)

    # ---- apply page (one page for all jobs) + data it reads
    os.makedirs(os.path.join(OUT, "data"), exist_ok=True)
    json.dump({j["slug"]: [j["title"], j["company"], j["apply_url"]] for j in jobs},
              open(os.path.join(OUT, "data", "apply.json"), "w"), separators=(",", ":"))
    write("/apply/", f"""{AD_LEADER}<section class="wrap article center" id="applyBox" data-wait="{APPLY_WAIT_SECONDS}">
<h1 id="aTitle">Continue to application</h1><p class="job-co big" id="aCo"></p>
<p id="aHost"></p>{AD_BOX}
<p><a id="go" class="btn-accent big-btn" href="/jobs/" rel="nofollow noopener" target="_blank">Continue to application &rarr;</a></p>
<p class="muted">Tip: a real employer will never ask you to pay for training, equipment or a background check.</p>
<p><a id="back" href="/jobs/">&larr; Back to jobs</a></p></section>""",
          f"Apply | {BRAND}", "Continue to the employer's application page.", robots="noindex, nofollow", canonical=False)

    # ---- search index (small)
    json.dump([{"t": j["title"], "c": j["company"], "u": f"/job/{j['slug']}/", "l": location_label(j),
                "ty": TYPE_LABEL.get(j.get("employment_type"), ""), "d": j["date_posted"]} for j in jobs],
              open(os.path.join(OUT, "data", "search.json"), "w"), separators=(",", ":"))
    write("/search/", f"""<section class="hero hero-small"><div class="wrap"><nav class="crumbs"><a href="/">Home</a> / Search</nav>
<h1>Search Remote Jobs</h1><form class="hero-search left" action="/search/" method="get" role="search">
<input type="search" name="q" id="q" placeholder="Job title, skill or company" aria-label="Search"><button type="submit">Search</button></form></div></section>
{AD_LEADER}<section class="wrap jobs"><p class="muted" id="sCount"></p><div class="job-list" id="sResults"></div></section>""",
          f"Search Remote Jobs | {BRAND}", "Search remote jobs by title, skill or company.", robots="noindex, follow")

    # ---- all jobs + categories
    urls += paged("/jobs/", jobs, "Latest Remote Jobs", f"Browse {len(jobs):,} remote jobs hiring now from employers' own career pages. Updated daily.",
                  '<p class="lead">Fresh remote jobs from company career pages, updated every day.</p>', "Jobs")
    counts = {}
    for slug, name, short, rx, intro in CATEGORIES:
        cj = [j for j in jobs if slug in j["cats"]]
        counts[slug] = len(cj)
        others = "".join(f'<a class="pill" href="/{c[0]}/">{c[2]}</a>' for c in CATEGORIES if c[0] != slug)
        urls += paged(f"/{slug}/", cj, name, f"{len(cj):,} {name.lower()} hiring now. Updated daily, apply on the employer's own site.",
                      f'<p class="lead">{intro}</p><div class="pills">{others}</div>', name)

    # ---- home
    pills = "".join(f'<a class="pill" href="/{c[0]}/">{c[2]} <span class="count">{counts[c[0]]:,}</span></a>' for c in CATEGORIES)
    guides = "".join(f'<a class="card post-card" href="/blog/{p["slug"]}/"><h3>{p["title"]}</h3><p>{p["desc"]}</p><span class="more">Read guide &rarr;</span></a>' for p in POSTS)
    faq = [("Are the jobs on this site real?", "Yes. Jobs come straight from employers' own career pages and are refreshed every day. When a company closes a job, it disappears here too."),
           ("Is it free to apply?", "Yes. Applying is always free. A real employer will never ask you to pay for training, equipment or a background check."),
           ("Where do I apply?", "Every Apply button takes you to the employer's own application page."),
           ("Can I work from any country?", "It depends on the job. Each listing shows which countries or regions the employer hires from.")]
    faq_html = "".join(f"<details><summary>{q}</summary><p>{a}</p></details>" for q, a in faq)
    home = f"""<section class="hero"><div class="wrap">
<p class="badge"><span class="dot"></span> {len(jobs):,} remote jobs &middot; updated daily</p>
<h1>Remote Jobs Hiring Now</h1>
<p class="lead">Real work-from-home jobs from company career pages: customer service, software, data, marketing, sales, design and more.</p>
<form class="hero-search" action="/search/" method="get" role="search"><input type="search" name="q" placeholder="Job title, skill or company" aria-label="Search remote jobs"><button type="submit">Search Jobs</button></form>
</div></section>
<section class="wrap" id="categories"><h2>Browse Remote Jobs by Category</h2><div class="pills">{pills}</div></section>
{AD_LEADER}
<section class="wrap jobs"><h2>Latest Remote Jobs</h2>{job_list(jobs[:30])}<div class="center"><a class="btn" href="/jobs/">See all {len(jobs):,} jobs</a></div></section>
{AD_BOX}
<section class="wrap"><h2>Remote Job Guides</h2><div class="grid">{guides}</div></section>
<section class="wrap seo-text"><h2>Find Remote Work You Can Trust</h2><p>{BRAND} collects remote openings directly from employers' career pages every day, so listings are current and every application happens on the company's own site. Before applying anywhere, read our guide on <a href="/blog/how-to-spot-remote-job-scams/">how to spot remote job scams</a>.</p></section>
<section class="wrap faq"><h2>Frequently Asked Questions</h2>{faq_html}</section>"""
    write("/", home, f"Remote Jobs Hiring Now – Work From Home Jobs | {BRAND}",
          f"{len(jobs):,} remote jobs hiring now from company career pages: customer service, software, data, marketing, sales and more. Updated daily.",
          [{"@context": "https://schema.org", "@type": "WebSite", "name": BRAND, "url": BASE,
            "potentialAction": {"@type": "SearchAction", "target": BASE + "/search/?q={q}", "query-input": "required name=q"}},
           {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
               {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}])
    urls.insert(0, "/")

    # ---- blog
    cards = "".join(f'<a class="card post-card" href="/blog/{p["slug"]}/"><h2>{p["title"]}</h2><p>{p["desc"]}</p><span class="more">Read more &rarr;</span></a>' for p in POSTS)
    write("/blog/", f'<section class="hero hero-small"><div class="wrap"><nav class="crumbs"><a href="/">Home</a> / Blog</nav><h1>Remote Work Blog</h1><p class="lead">Honest, practical guides to help you find and land a remote job.</p></div></section><section class="wrap"><div class="grid">{cards}</div></section>',
          f"Remote Work Blog – Job Search Guides | {BRAND}", "Practical guides for finding remote jobs: avoiding scams, writing a remote resume, and getting hired.",
          [crumbs([("Home", "/"), ("Blog", "/blog/")])])
    urls.append("/blog/")
    for p in POSTS:
        rel = "".join(f'<li><a href="/blog/{o["slug"]}/">{o["title"]}</a></li>' for o in POSTS if o is not p)
        bodytxt = p["body"].replace("{brand}", BRAND).replace(
            "comes from a public remote job board, and the Apply button takes you to the original listing",
            "comes from an employer's own career page, and the Apply button takes you to the employer's application page")
        path = f"/blog/{p['slug']}/"
        write(path, f"""<article class="wrap article"><nav class="crumbs"><a href="/">Home</a> / <a href="/blog/">Blog</a> / {p['title']}</nav>
<h1>{p['title']}</h1><p class="muted">Updated {TODAY.strftime('%B %d, %Y')} &middot; {BRAND}</p>{bodytxt}{AD_BOX}
<div class="cta-box"><h2>Browse remote jobs hiring now</h2><p>{len(jobs):,} openings, updated daily.</p><a class="btn-accent" href="/jobs/">View Jobs</a></div>
<h2>Related Guides</h2><ul>{rel}</ul></article>""", f"{p['title']} | {BRAND}", p["desc"],
              [{"@context": "https://schema.org", "@type": "Article", "headline": p["title"], "description": p["desc"],
                "datePublished": p["date"], "dateModified": TODAY.isoformat(), "author": {"@type": "Organization", "name": BRAND},
                "publisher": {"@type": "Organization", "name": BRAND}, "mainEntityOfPage": BASE + path},
               crumbs([("Home", "/"), ("Blog", "/blog/"), (p["title"], path)])])
        urls.append(path)

    # ---- static pages
    pages = {
        "/about/": ("About Us", f"<p>{BRAND} helps people find real remote jobs without the noise. Every day we collect openings directly from employers' career pages, sort them into clear categories and send you to the employer's own page to apply.</p><p>We do not charge job seekers anything. If a job ever asks you for money, please do not pay and <a href=\"/contact/\">let us know</a>.</p>"),
        "/contact/": ("Contact Us", f'<p>Questions, feedback or a suspicious listing to report? Email <a href="mailto:{EMAIL}">{EMAIL}</a>.</p>'),
        "/post-a-job/": ("Post a Remote Job", f'<p>Hiring remotely? Send the job title, company, countries you hire from, salary range (if available) and your application link to <a href="mailto:{EMAIL}">{EMAIL}</a>. We review every listing before it goes live.</p>'),
        "/privacy-policy/": ("Privacy Policy", f"<p>Last updated: {TODAY.strftime('%B %d, %Y')}</p><h2>What we collect</h2><p>We do not ask you to create an account. Our hosting provider (Cloudflare) may keep standard logs such as IP address and browser type for security and performance.</p><h2>Job listings</h2><p>Jobs come from employers' public career pages. When you continue to an application, you leave our site and that employer's privacy policy applies.</p><h2>Advertising</h2><p>We show ads from Adsterra. Adsterra and its partners may use cookies or similar technologies to show and measure ads. You can limit cookies in your browser settings.</p><h2>Contact</h2><p>Questions? Email <a href=\"mailto:{EMAIL}\">{EMAIL}</a>.</p>"),
    }
    for path, (t, b) in pages.items():
        write(path, f'<article class="wrap article"><h1>{t}</h1>{b}</article>', f"{t} | {BRAND}", f"{t} – {BRAND}.")
        urls.append(path)
    write("/404.html", '<article class="wrap article"><h1>Page not found</h1><p>This job may have closed. <a href="/jobs/">See current remote jobs</a>.</p></article>',
          f"Page Not Found | {BRAND}", "Page not found.", robots="noindex", canonical=False)

    # ---- sitemaps (split every 40,000 URLs), robots
    chunks = [urls[i:i + 40000] for i in range(0, len(urls), 40000)]
    for n, ch in enumerate(chunks, 1):
        with open(os.path.join(OUT, f"sitemap-{n}.xml"), "w") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
            for u in ch:
                f.write(f"<url><loc>{esc(BASE + u)}</loc></url>\n")
            f.write("</urlset>\n")
    with open(os.path.join(OUT, "sitemap.xml"), "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for n in range(1, len(chunks) + 1):
            f.write(f"<sitemap><loc>{BASE}/sitemap-{n}.xml</loc><lastmod>{TODAY}</lastmod></sitemap>\n")
        f.write("</sitemapindex>\n")
    open(os.path.join(OUT, "robots.txt"), "w").write(
        f"User-agent: *\nDisallow: /apply/\nDisallow: /search/\nDisallow: /ads/\nDisallow: /data/\n\nSitemap: {BASE}/sitemap.xml\n")
    total = sum(len(fs) for _, _, fs in os.walk(OUT))
    print(f"Built {FILES} pages, {len(urls)} URLs in sitemap, {total} files total (Cloudflare limit 20,000).", file=sys.stderr)
    if total > 19500:
        sys.exit("Too many files for Cloudflare Pages. Lower MAX_JOBS in build.py.")


if __name__ == "__main__":
    main()
