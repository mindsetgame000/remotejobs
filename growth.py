"""Extra page types built from the live job data:
- collection pages (entry level, part-time, worldwide, chat support, no degree ...)
- country pages and country x category pages (only when there are enough real jobs)
- the monthly remote jobs report
- free tools (/tools/...) and "$X an hour is how much a year" pay pages
build.py calls prepare() once, then build_all(). Every page links to the others."""
import datetime, re
from collections import Counter
from tools import TOOLS

b = None          # the build module (set in prepare)
JOBS = []
COUNTRY_PAGES = {}   # country -> (path, specific_count)
CC_PAGES = {}        # (cat_slug, country) -> path
ACTIVE_COLLECTIONS = {}  # slug -> count
MIN_COUNTRY = 5
MIN_COUNTRY_CAT = 5
HOURLY_RANGE = range(10, 51)               # $10 ... $50 an hour
YEARLY_RANGE = range(25000, 125001, 5000)  # $25,000 ... $125,000 a year

THE = {"United States", "United Kingdom", "Philippines", "Netherlands", "United Arab Emirates",
       "Czech Republic", "Dominican Republic", "Bahamas"}

SENIOR = re.compile(r"\b(senior|sr\.?|lead|manager|director|principal|staff|head|vp|chief|architect)\b", re.I)
COLLECTIONS = [
    ("entry-level-remote-jobs", "Entry Level Remote Jobs",
     "Remote jobs for beginners: junior, trainee, associate-level and internship roles, plus listings that say no experience is required or training is provided.",
     lambda j: not SENIOR.search(j["title"]) and (
         re.search(r"\b(junior|jr\b|entry[- ]?level|graduate|trainee|apprentice|intern|internship|new grad|tier (1|i)\b|level (1|i)\b)", j["title"], re.I)
         or re.search(r"no (prior |previous )?experience (is )?(required|necessary|needed)|entry[- ]level (role|position|job)|(paid )?training (is )?provided|we will train you|0[- ]?(to|-)[- ]?1 years?", j["_text"]))),
    ("part-time-remote-jobs", "Part-Time Remote Jobs",
     "Part-time remote jobs with fewer hours a week: good for students, parents and anyone who wants flexible work from home.",
     lambda j: j.get("employment_type") == "PART_TIME" or re.search(r"part[- ]?time", j["title"], re.I)),
    ("worldwide-remote-jobs", "Work From Anywhere Remote Jobs",
     "Remote jobs that hire worldwide. These employers say you can work from anywhere, or they accept applicants from a long list of countries.",
     lambda j: j.get("worldwide")),
    ("remote-chat-support-jobs", "Remote Chat Support Jobs (Non-Phone)",
     "Customer support jobs done mostly by live chat, email and tickets instead of phone calls. Great if you prefer writing to talking.",
     lambda j: "remote-customer-service-jobs" in j["cats"]
     and re.search(r"\b(chat|email|e-mail|non[- ]?voice|written|ticket)", j["title"].lower() + " " + j["_text"][:3000])
     and not re.search(r"\b(phone|call cent|voice|outbound|inbound call)", j["title"], re.I)),
    ("freelance-contract-remote-jobs", "Freelance & Contract Remote Jobs",
     "Freelance, contract and independent contractor remote jobs. You usually set your own schedule and invoice for your time.",
     lambda j: j.get("employment_type") == "CONTRACTOR" or re.search(r"\b(freelance|contract(or)?)\b", j["title"], re.I)),
    ("high-paying-remote-jobs", "High Paying Remote Jobs ($100K+)",
     "Remote jobs that pay $100,000 a year or more (or $50+ an hour), based on the salary range the employer published.",
     lambda j: (annual(j) or 0) >= 100000),
    ("remote-jobs-no-degree", "Remote Jobs Without a Degree",
     "Remote jobs whose listing says a college degree is not required, or that a high school diploma or GED is enough.",
     lambda j: re.search(r"no (college |university |four-year |4-year )?degree (is )?(required|needed|necessary)|degree (is )?not required|without a (college )?degree|high school diploma|\bged\b", j["_text"])),
    ("remote-internships", "Remote Internships",
     "Paid and unpaid remote internships for students and recent graduates.",
     lambda j: j.get("employment_type") == "INTERN" or re.search(r"\bintern(ship)?\b", j["title"], re.I)),
    ("night-shift-remote-jobs", "Night Shift Remote Jobs",
     "Remote jobs with night, overnight or evening shifts, often in customer support for US and European customers.",
     lambda j: re.search(r"night shift|overnight|graveyard|evening shift|night-shift", j["title"].lower() + " " + j["_text"][:4000])),
    ("weekend-remote-jobs", "Weekend Remote Jobs",
     "Remote jobs with weekend shifts or weekend-only schedules.",
     lambda j: re.search(r"weekend", j["title"], re.I) or re.search(r"weekend (shift|availability|schedule)|work(ing)? weekends|saturday and sunday", j["_text"][:4000])),
]


# ------------------------------------------------------------------ helpers
def esc(s):
    return b.esc(s)


def the(c):
    return f"the {c}" if c in THE else c


def annual(j):
    """Yearly USD pay from the listed salary (midpoint of the range), or None."""
    if (j.get("salary_currency") or "USD") != "USD":
        return None
    try:
        vals = [float(v) for v in (j.get("salary_min"), j.get("salary_max")) if v not in (None, "")]
    except ValueError:
        return None
    if not vals:
        return None
    v = sum(vals) / len(vals)
    mult = {"HOUR": 2080, "DAY": 260, "WEEK": 52, "MONTH": 12, "YEAR": 1, "": 1}.get(j.get("salary_unit") or "", 1)
    if not j.get("salary_unit") and v < 300:      # a bare small number is an hourly rate
        mult = 2080
    a = v * mult
    return a if 5000 <= a <= 1000000 else None


def money(v):
    return "${:,.0f}".format(v)


def money2(v):
    return "${:,.2f}".format(v)


def pills(items):
    return '<div class="pills">' + "".join(f'<a class="pill" href="{u}">{esc(n)}</a>' for n, u in items) + "</div>" if items else ""


def tool_path(t):
    return f"/tools/{t['slug']}/"


def hourly_path(n):
    return f"/{n}-an-hour-is-how-much-a-year/"


def yearly_path(n):
    return f"/{n}-a-year-is-how-much-an-hour/"


def cat_names():
    return {c[0]: c[1] for c in b.CATEGORIES}


# ------------------------------------------------------------------ prepare
def prepare(build_module, jobs):
    global b, JOBS
    b, JOBS = build_module, jobs
    for j in jobs:
        j["_text"] = b.plain(j.get("description", "")).lower()
        j["_annual"] = annual(j)
    for slug, name, intro, test in COLLECTIONS:
        ACTIVE_COLLECTIONS[slug] = sum(1 for j in jobs if test(j))
    cc = Counter(c for j in jobs for c in (j.get("applicant_countries") or []))
    for c, n in cc.items():
        if n >= MIN_COUNTRY:
            COUNTRY_PAGES[c] = (f"/remote-jobs-{b.slugify(c)}/", n)
    for slug, *_ in b.CATEGORIES:
        cnt = Counter(c for j in jobs if slug in j["cats"] for c in (j.get("applicant_countries") or []))
        for c, n in cnt.items():
            if n >= MIN_COUNTRY_CAT and c in COUNTRY_PAGES:
                CC_PAGES[(slug, c)] = f"/{slug}-{b.slugify(c)}/"
    prepare2(jobs)


def collections_list(min_jobs=3):
    return [(name, f"/{slug}/") for slug, name, _, _ in COLLECTIONS if ACTIVE_COLLECTIONS.get(slug, 0) >= min_jobs]


def top_countries(n=12):
    return sorted(COUNTRY_PAGES.items(), key=lambda kv: -kv[1][1])[:n]


def link_phrases():
    out = []
    for slug, name, _, _ in COLLECTIONS:
        if ACTIVE_COLLECTIONS.get(slug, 0) >= 3:
            out.append((re.sub(r"\s*\(.*?\)", "", name).lower(), f"/{slug}/"))
    out += [("work from anywhere", "/worldwide-remote-jobs/"), ("remote jobs worldwide", "/worldwide-remote-jobs/"),
            ("chat support jobs", "/remote-chat-support-jobs/"), ("no experience", "/entry-level-remote-jobs/"),
            ("remote jobs report", "/remote-jobs-report/"), ("free tools", "/tools/")]
    for c, (path, _) in COUNTRY_PAGES.items():
        out += [(f"remote jobs in {the(c)}".lower(), path), (f"remote jobs {c}".lower(), path)]
    for t in TOOLS:
        out += [(p, tool_path(t)) for p in t["phrases"]]
    for s_, (n, p, _) in SKILL_PAGES.items():
        out.append((f"remote {n.lower()} jobs", p))
    return out


# ------------------------------------------------------------------ bits used by build.py
def category_extra(slug):
    """Country links + tools box for a category page."""
    names = cat_names()
    cs = sorted([(c, p) for (s, c), p in CC_PAGES.items() if s == slug], key=lambda x: x[0])
    html = ""
    if cs:
        html += f'<section class="wrap"><h2>{esc(names[slug])} by Country</h2>' + pills(
            [(f"{names[slug].replace('Remote ', '').replace(' Jobs', '')} in {c}", p) for c, p in cs]) + "</section>"
    ts = [t for t in TOOLS if slug in t["cats"]] or TOOLS[:2]
    html += '<section class="wrap"><h2>Free Tools for Your Job Search</h2>' + pills(
        [(t["name"], tool_path(t)) for t in ts] + [("Remote jobs report", "/remote-jobs-report/")]) + "</section>"
    return html


def job_links(j):
    bits = []
    a = j.get("_annual")
    if a and j.get("salary_unit") == "HOUR":
        h = round(a / 2080)
        if h in HOURLY_RANGE:
            bits.append(f'<a href="{hourly_path(h)}">How much is ${h} an hour per year?</a>')
    elif a:
        y = int(round(a / 5000.0) * 5000)
        if y in YEARLY_RANGE:
            bits.append(f'<a href="{yearly_path(y)}">{money(y)} a year is how much an hour?</a>')
    for c in (j.get("applicant_countries") or [])[:3]:
        if c in COUNTRY_PAGES:
            bits.append(f'<a href="{COUNTRY_PAGES[c][0]}">More remote jobs in {esc(the(c))}</a>')
    if j.get("worldwide"):
        bits.append('<a href="/worldwide-remote-jobs/">Other work-from-anywhere jobs</a>')
    bits.append('<a href="/tools/cover-letter-generator/">Write a cover letter for this job</a>')
    return '<p class="muted job-links">' + " &middot; ".join(bits) + "</p>"


def home_html():
    pop = collections_list() + [(f"Remote Jobs in {the(c)}", p) for c, (p, _) in top_countries(8)]
    tools = "".join(f'<a class="card post-card" href="{tool_path(t)}"><h3>{esc(t["name"])}</h3><p>{esc(t["intro"][:120])}…</p><span class="more">Open tool &rarr;</span></a>' for t in TOOLS)
    top_cos = sorted(COMPANY_PAGES.items(), key=lambda kv: -sum(1 for j in JOBS if j["company"] == kv[0]))[:16]
    extra = (f'<section class="wrap"><h2>Top Companies Hiring Remotely</h2>{pills([(n, p) for n, p in top_cos] + [("All companies", "/companies/")])}</section>' if top_cos else "")
    extra += (f'<section class="wrap"><h2>Remote Jobs by Skill</h2>{pills([(n, p) for n, p, _ in SKILL_PAGES.values()])}</section>' if SKILL_PAGES else "")
    return (extra + f'<section class="wrap"><h2>Popular Remote Job Searches</h2>{pills(pop)}</section>'
            f'<section class="wrap"><h2>Free Job Search Tools</h2><div class="grid">{tools}</div>'
            f'<p class="muted">Plus our <a href="/remote-jobs-report/">monthly remote jobs report</a> with salaries and top hiring companies.</p></section>')


def footer_columns():
    pop = "".join(f'<li><a href="{u}">{esc(n)}</a></li>' for n, u in collections_list()[:6])
    pop += "".join(f'<li><a href="{p}">Remote Jobs in {esc(the(c))}</a></li>' for c, (p, _) in top_countries(4))
    tools = "".join(f'<li><a href="{tool_path(t)}">{esc(t["name"])}</a></li>' for t in TOOLS)
    tools += '<li><a href="/remote-jobs-report/">Remote Jobs Report</a></li><li><a href="/companies/">Companies Hiring</a></li>'
    return f'<div><h3>Popular Searches</h3><ul>{pop}</ul></div><div><h3>Free Tools</h3><ul>{tools}</ul></div>'


# ------------------------------------------------------------------ page builders
def build_all():
    urls = []
    urls += build_collections()
    urls += build_countries()
    urls += build_report()
    urls += build_tools()
    urls += build_pay_pages()
    return urls


def build_collections():
    urls = []
    for slug, name, intro, test in COLLECTIONS:
        cj = [j for j in JOBS if test(j)]
        others = pills([(n, u) for n, u in collections_list() if u != f"/{slug}/"])
        cats = Counter(c for j in cj for c in j["cats"]).most_common(6)
        names = cat_names()
        cat_line = (" The most common types are " + ", ".join(f'<a href="/{c}/">{esc(names[c].lower())}</a> ({n})' for c, n in cats) + ".") if cats else ""
        urls += b.paged(f"/{slug}/", cj, name,
                        f"{len(cj):,} {name.lower()} hiring now, from employers' own career pages. Updated daily.",
                        f'<p class="lead">{esc(intro)}{cat_line}</p>{others}', name, category_extra_generic())
    return urls


def category_extra_generic():
    return '<section class="wrap"><h2>Free Tools</h2>' + pills([(t["name"], tool_path(t)) for t in TOOLS]) + "</section>"


def country_intro(c, jobs_specific, n_world):
    names = cat_names()
    cats = Counter(x for j in jobs_specific for x in j["cats"]).most_common(4)
    cos = Counter(j["company"] for j in jobs_specific).most_common(5)
    txt = (f"{len(jobs_specific):,} remote jobs are open to applicants in {esc(the(c))} right now, from employers such as "
           f"{esc(', '.join(x for x, _ in cos))}.")
    if cats:
        txt += " The biggest categories are " + ", ".join(
            (f'<a href="{CC_PAGES[(x, c)]}">{esc(names[x].lower())}</a>' if (x, c) in CC_PAGES else esc(names[x].lower())) + f" ({n})"
            for x, n in cats) + "."
    if n_world:
        txt += f' We also list <a href="/worldwide-remote-jobs/">{n_world:,} work-from-anywhere jobs</a> that accept applicants from any country, shown below the country-specific openings.'
    return f'<p class="lead">{txt}</p>'


def build_countries():
    urls = []
    world = [j for j in JOBS if j.get("worldwide")]
    names = cat_names()
    for c, (path, n) in COUNTRY_PAGES.items():
        spec = [j for j in JOBS if c in (j.get("applicant_countries") or [])]
        ids = {id(j) for j in spec}
        allj = spec + [j for j in world if id(j) not in ids]
        cc = sorted([(names[s], p) for (s, cn), p in CC_PAGES.items() if cn == c])
        extra = (f'<section class="wrap"><h2>Remote Jobs in {esc(the(c))} by Category</h2>{pills(cc)}</section>' if cc else "")
        extra += ('<section class="wrap"><h2>Other Countries</h2>' + pills(
            [(f"Remote Jobs in {the(x)}", p) for x, (p, _) in top_countries(16) if x != c]) + "</section>")
        extra += category_extra_generic()
        urls += b.paged(path, allj, f"Remote Jobs in {the(c)}",
                        f"{n:,} remote jobs open to applicants in {the(c)}, plus work-from-anywhere roles. Updated daily.",
                        country_intro(c, spec, len(allj) - len(spec)), f"Remote Jobs in {the(c)}", extra)
    for (slug, c), path in CC_PAGES.items():
        cj = [j for j in JOBS if slug in j["cats"] and c in (j.get("applicant_countries") or [])]
        short = names[slug]
        title = f"{short} in {the(c)}"
        cos = Counter(j["company"] for j in cj).most_common(5)
        intro = (f'<p class="lead">{len(cj):,} {esc(short.lower())} are open to people living in {esc(the(c))}, '
                 f'with employers such as {esc(", ".join(x for x, _ in cos))}. See also all <a href="/{slug}/">{esc(short.lower())}</a> '
                 f'and every <a href="{COUNTRY_PAGES[c][0]}">remote job in {esc(the(c))}</a>.</p>')
        urls += b.paged(path, cj, title, f"{len(cj):,} {short.lower()} open to applicants in {the(c)}. Apply on the employer's site.",
                        intro, title, category_extra(slug))
    return urls


def build_report():
    names = cat_names()
    today = b.TODAY
    month = today.strftime("%B %Y")
    jobs = JOBS
    n = len(jobs)
    if not n:
        return []
    week = sum(1 for j in jobs if j["date_posted"] >= (today - datetime.timedelta(days=7)).isoformat())
    paid = [j for j in jobs if j.get("_annual")]
    rows = ""
    for slug, name, *_ in b.CATEGORIES:
        cj = [j for j in jobs if slug in j["cats"]]
        if not cj:
            continue
        pays = sorted(j["_annual"] for j in cj if j.get("_annual"))
        med = money(pays[len(pays) // 2]) if len(pays) >= 3 else "–"
        top = Counter(j["company"] for j in cj).most_common(1)[0][0]
        rows += (f'<tr><td><a href="/{slug}/">{esc(name)}</a></td><td>{len(cj):,}</td><td>{round(100 * len(pays) / len(cj))}%</td>'
                 f'<td>{med}</td><td>{esc(top)}</td></tr>')
    cos = Counter(j["company"] for j in jobs).most_common(15)
    co_rows = "".join(f"<tr><td>{i + 1}</td><td>{esc(c)}</td><td>{k}</td></tr>" for i, (c, k) in enumerate(cos))
    ctr = Counter(c for j in jobs for c in (j.get("applicant_countries") or [])).most_common(12)
    def clink(c):
        return f'<a href="{COUNTRY_PAGES[c][0]}">{esc(c)}</a>' if c in COUNTRY_PAGES else esc(c)
    ctr_rows = "".join(f"<tr><td>{clink(c)}</td><td>{k:,}</td><td>{round(100 * k / n)}%</td></tr>" for c, k in ctr)
    types = Counter(b.TYPE_LABEL.get(j.get("employment_type"), "Not stated") for j in jobs).most_common()
    type_rows = "".join(f"<tr><td>{esc(t)}</td><td>{k:,}</td><td>{round(100 * k / n)}%</td></tr>" for t, k in types)
    coll = "".join(f'<li><a href="/{s}/">{esc(nm)}</a>: {ACTIVE_COLLECTIONS.get(s, 0):,} open jobs</li>' for s, nm, _, _ in COLLECTIONS if ACTIVE_COLLECTIONS.get(s, 0))
    all_pay = sorted(j["_annual"] for j in paid)
    med_all = money(all_pay[len(all_pay) // 2]) if all_pay else "–"
    top_cat = max(((s, sum(1 for j in jobs if s in j["cats"])) for s, *_ in b.CATEGORIES), key=lambda x: x[1])
    faq = [
        (f"How many remote jobs are open in {month}?", f"We are tracking {n:,} open remote jobs from {len(set(j['company'] for j in jobs)):,} companies as of {today.strftime('%B %d, %Y')}, with {week:,} posted in the last 7 days."),
        ("What is the median salary for remote jobs?", f"Across the {len(paid):,} listings that publish pay, the median is {med_all} a year (hourly pay converted at 2,080 hours a year)."),
        ("Which remote job category has the most openings?", f"{names[top_cat[0]]} has the most openings right now, with {top_cat[1]:,} jobs."),
        ("Which companies are hiring the most remote workers?", "The top remote employers this month are " + ", ".join(c for c, _ in cos[:5]) + "."),
    ]
    faq_html = "".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in faq)
    body = f"""<section class="hero hero-small"><div class="wrap"><nav class="crumbs"><a href="/">Home</a> / Remote Jobs Report</nav>
<h1>Remote Jobs Report: {month}</h1>
<p class="lead">A live snapshot of the remote job market, built from {n:,} open jobs on employers' own career pages. Updated every day; last update {today.strftime('%B %d, %Y')}.</p></div></section>
{b.AD_LEADER}
<section class="wrap"><div class="facts"><h2>Key numbers</h2><dl>
<dt>Open remote jobs</dt><dd>{n:,}</dd><dt>Hiring companies</dt><dd>{len(set(j['company'] for j in jobs)):,}</dd>
<dt>Posted in the last 7 days</dt><dd>{week:,}</dd><dt>Listings that show pay</dt><dd>{len(paid):,} ({round(100 * len(paid) / n)}%)</dd>
<dt>Median published pay</dt><dd>{med_all} a year</dd><dt>Work-from-anywhere jobs</dt><dd>{ACTIVE_COLLECTIONS.get('worldwide-remote-jobs', 0):,}</dd></dl></div></section>
<section class="wrap"><h2>Remote jobs and pay by category</h2><div class="table-wrap"><table class="data-table"><thead><tr><th>Category</th><th>Open jobs</th><th>Show pay</th><th>Median pay / year</th><th>Top employer</th></tr></thead><tbody>{rows}</tbody></table></div>
<p class="muted">Median pay uses the midpoint of each published range in US dollars; hourly rates are converted at 2,080 hours a year. Shown only when at least 3 jobs list pay.</p></section>
{b.AD_BOX}
<section class="wrap"><h2>Top 15 companies hiring remotely</h2><div class="table-wrap"><table class="data-table"><thead><tr><th>#</th><th>Company</th><th>Open remote jobs</th></tr></thead><tbody>{co_rows}</tbody></table></div></section>
<section class="wrap"><h2>Where remote employers hire</h2><div class="table-wrap"><table class="data-table"><thead><tr><th>Country</th><th>Jobs open to it</th><th>Share</th></tr></thead><tbody>{ctr_rows}</tbody></table></div>
<p class="muted">A job can accept several countries, so shares add up to more than 100%.</p></section>
<section class="wrap"><h2>Job types</h2><div class="table-wrap"><table class="data-table"><thead><tr><th>Type</th><th>Jobs</th><th>Share</th></tr></thead><tbody>{type_rows}</tbody></table></div></section>
<section class="wrap seo-text"><h2>Popular kinds of remote work</h2><ul>{coll}</ul>
<p>Want to turn an hourly rate into a yearly salary? Try the <a href="/tools/hourly-to-salary-calculator/">hourly to salary calculator</a>. You may use these figures with a link back to this page.</p></section>
<section class="wrap faq"><h2>FAQ</h2>{faq_html}</section>"""
    schemas = [b.crumbs([("Home", "/"), ("Remote Jobs Report", "/remote-jobs-report/")]),
               {"@context": "https://schema.org", "@type": "Article", "headline": f"Remote Jobs Report: {month}",
                "datePublished": today.replace(day=1).isoformat(), "dateModified": today.isoformat(),
                "author": {"@type": "Organization", "name": b.BRAND}, "publisher": {"@type": "Organization", "name": b.BRAND},
                "mainEntityOfPage": b.BASE + "/remote-jobs-report/"},
               {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
                   {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}]
    b.write("/remote-jobs-report/", body, f"Remote Jobs Report {month}: Salaries, Top Companies & Countries | {b.BRAND}",
            f"Live remote job market data for {month}: {n:,} open jobs, median pay by category, top hiring companies and countries.", schemas)
    b.LASTMOD["/remote-jobs-report/"] = today.isoformat()
    return ["/remote-jobs-report/"]


def build_tools():
    names = cat_names()
    urls = []
    cards = "".join(f'<a class="card post-card" href="{tool_path(t)}"><h2>{esc(t["name"])}</h2><p>{esc(t["intro"])}</p><span class="more">Open tool &rarr;</span></a>' for t in TOOLS)
    b.write("/tools/", f"""<section class="hero hero-small"><div class="wrap"><nav class="crumbs"><a href="/">Home</a> / Tools</nav>
<h1>Free Tools for Remote Job Seekers</h1><p class="lead">Simple, free tools that help you find and land a remote job: check your typing speed, convert pay, spot scam offers, write a cover letter and line up time zones. Everything runs in your browser.</p></div></section>
{b.AD_LEADER}<section class="wrap"><div class="grid">{cards}</div></section>{b.AD_BOX}""",
            f"Free Tools for Remote Job Seekers | {b.BRAND}", "Free tools for remote job seekers: typing speed test, hourly to salary calculator, job scam checker, cover letter generator and time zone converter.",
            [b.crumbs([("Home", "/"), ("Tools", "/tools/")])])
    urls.append("/tools/")
    b.LASTMOD["/tools/"] = b.TODAY.isoformat()
    for t in TOOLS:
        path = tool_path(t)
        cat = t["cats"][0]
        cj = [j for j in JOBS if cat in j["cats"]][:5]
        faq_html = "".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in t["faq"])
        others = pills([(o["name"], tool_path(o)) for o in TOOLS if o is not t])
        extra = ""
        if t["slug"] == "hourly-to-salary-calculator":
            extra = ('<section class="wrap"><h2>Quick answers: hourly to yearly</h2>' + pills([(f"${n}/hour", hourly_path(n)) for n in HOURLY_RANGE]) +
                     '<h2>Quick answers: yearly to hourly</h2>' + pills([(f"{money(n)}/year", yearly_path(n)) for n in YEARLY_RANGE]) + "</section>")
        body = f"""<section class="hero hero-small"><div class="wrap"><nav class="crumbs"><a href="/">Home</a> / <a href="/tools/">Tools</a> / {esc(t['name'])}</nav>
<h1>{esc(t['name'])}</h1><p class="lead">{esc(t['intro'])}</p></div></section>
<section class="wrap">{t['html']}</section>
<script>{t['js']}</script>
{b.AD_LEADER}
<article class="wrap article">{t['howto']}</article>
{extra}
{b.AD_BOX}
{f'<section class="wrap"><h2>Latest {esc(names[cat])}</h2>{b.job_list(cj)}<p><a href="/{cat}/">See all {esc(names[cat].lower())} &rarr;</a></p></section>' if cj else ''}
<section class="wrap"><h2>Related job categories</h2>{pills([(names[c], f"/{c}/") for c in t["cats"] if c in names])}</section>
<section class="wrap faq"><h2>FAQ</h2>{faq_html}</section>
<section class="wrap"><h2>More free tools</h2>{others}</section>"""
        schemas = [b.crumbs([("Home", "/"), ("Tools", "/tools/"), (t["name"], path)]),
                   {"@context": "https://schema.org", "@type": "WebApplication", "name": t["name"], "url": b.BASE + path,
                    "applicationCategory": "BusinessApplication", "operatingSystem": "Any", "description": t["desc"],
                    "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}},
                   {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
                       {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in t["faq"]]}]
        b.write(path, body, f"{t['title']} | {b.BRAND}", t["desc"], schemas)
        urls.append(path)
        b.LASTMOD[path] = b.TODAY.isoformat()
    return urls


def _pay_table(hourly):
    rows = [("Hourly", hourly), ("Daily (8 hours)", hourly * 8), ("Weekly (40 hours)", hourly * 40),
            ("Bi-weekly", hourly * 80), ("Monthly", hourly * 2080 / 12), ("Yearly", hourly * 2080)]
    return '<table class="data-table pay"><tbody>' + "".join(f"<tr><th>{r}</th><td>{money2(v)}</td></tr>" for r, v in rows) + "</tbody></table>"


def _part_time(hourly):
    rows = "".join(f"<tr><td>{h} hours/week</td><td>{money(hourly * h)}</td><td>{money(hourly * h * 52 / 12)}</td><td>{money(hourly * h * 52)}</td></tr>" for h in (10, 20, 30, 40))
    return f'<div class="table-wrap"><table class="data-table"><thead><tr><th>Schedule</th><th>Weekly</th><th>Monthly</th><th>Yearly</th></tr></thead><tbody>{rows}</tbody></table></div>'


def _jobs_near(yearly, n=8):
    pool = [j for j in JOBS if j.get("_annual") and abs(j["_annual"] - yearly) <= max(4000, yearly * 0.12)]
    pool.sort(key=lambda j: (abs(j["_annual"] - yearly), j["date_posted"]))
    return pool[:n]


def build_pay_pages():
    urls = []
    year = b.TODAY.year
    for h in HOURLY_RANGE:
        path = hourly_path(h)
        y = h * 2080
        near = _jobs_near(y)
        nav = pills([(f"${x} an hour", hourly_path(x)) for x in (h - 2, h - 1, h + 1, h + 2) if x in HOURLY_RANGE] +
                    [("Hourly to salary calculator", "/tools/hourly-to-salary-calculator/")])
        yl = int(round(y / 5000.0) * 5000)
        faq = [(f"How much is ${h} an hour per year?", f"${h} an hour is {money(y)} a year, based on 40 hours a week for 52 weeks (2,080 hours), before taxes."),
               (f"How much is ${h} an hour per month?", f"${h} an hour is about {money(y / 12)} a month at 40 hours a week."),
               (f"How much is ${h} an hour part-time?", f"At 20 hours a week, ${h} an hour is {money(h * 20 * 52)} a year, or {money(h * 20 * 52 / 12)} a month.")]
        faq_html = "".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in faq)
        body = f"""<article class="wrap article"><nav class="crumbs"><a href="/">Home</a> / <a href="/tools/hourly-to-salary-calculator/">Salary calculator</a> / ${h} an hour</nav>
<h1>${h} an Hour Is How Much a Year?</h1>
<p class="lead-small"><b>${h} an hour is {money(y)} a year</b> if you work 40 hours a week, 52 weeks a year. That is about {money(y / 12)} a month, {money(h * 80)} every two weeks and {money(h * 40)} a week, before taxes.</p>
{_pay_table(h)}
{b.AD_BOX}
<h2>${h} an hour on a part-time schedule</h2>{_part_time(h)}
<h2>With unpaid time off</h2><p>If you take two weeks off without pay (50 working weeks), ${h} an hour comes to {money(h * 40 * 50)} a year. Contractors and freelancers usually do not get paid holidays, so this number is often closer to what they really earn.</p>
<h2>Remote jobs paying about ${h} an hour</h2>
{b.job_list(near) if near else '<p class="muted">No current listings near this rate. Browse <a href="/jobs/">all remote jobs</a>.</p>'}
<h2>Compare other hourly rates</h2>{nav}
{f'<p>Going the other way? See <a href="{yearly_path(yl)}">{money(yl)} a year is how much an hour</a>.</p>' if yl in YEARLY_RANGE else ''}
<section class="faq"><h2>FAQ</h2>{faq_html}</section></article>"""
        b.write(path, body, f"${h} an Hour Is How Much a Year? ({year} Pay Breakdown) | {b.BRAND}",
                f"${h} an hour is {money(y)} a year, {money(y / 12)} a month and {money(h * 40)} a week at full time. See part-time pay and remote jobs paying ${h}/hour.",
                [b.crumbs([("Home", "/"), ("Salary calculator", "/tools/hourly-to-salary-calculator/"), (f"${h} an hour", path)]),
                 {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
                     {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}])
        urls.append(path)
        b.LASTMOD[path] = b.TODAY.replace(day=1).isoformat()
    for y in YEARLY_RANGE:
        path = yearly_path(y)
        h = y / 2080
        near = _jobs_near(y)
        nav = pills([(f"{money(x)} a year", yearly_path(x)) for x in (y - 10000, y - 5000, y + 5000, y + 10000) if x in YEARLY_RANGE] +
                    [("Hourly to salary calculator", "/tools/hourly-to-salary-calculator/")])
        faq = [(f"How much is {money(y)} a year per hour?", f"{money(y)} a year is about {money2(h)} an hour, based on 2,080 working hours a year."),
               (f"How much is {money(y)} a year per month?", f"{money(y)} a year is {money(y / 12)} a month before taxes."),
               (f"How much is {money(y)} a year every two weeks?", f"Paid bi-weekly (26 paychecks), {money(y)} a year is {money(y / 26)} per paycheck before taxes.")]
        faq_html = "".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in faq)
        hr = round(h)
        body = f"""<article class="wrap article"><nav class="crumbs"><a href="/">Home</a> / <a href="/tools/hourly-to-salary-calculator/">Salary calculator</a> / {money(y)} a year</nav>
<h1>{money(y)} a Year Is How Much an Hour?</h1>
<p class="lead-small"><b>{money(y)} a year is about {money2(h)} an hour</b> at 40 hours a week and 52 weeks a year. That works out to {money(y / 12)} a month, {money(y / 26)} every two weeks and {money(y / 52)} a week, before taxes.</p>
{_pay_table(h)}
{b.AD_BOX}
<h2>If you work fewer hours</h2><p>At 35 hours a week, {money(y)} a year is {money2(y / (35 * 52))} an hour. At 30 hours a week it is {money2(y / (30 * 52))} an hour.</p>
<h2>Remote jobs paying around {money(y)}</h2>
{b.job_list(near) if near else '<p class="muted">No current listings near this salary. Browse <a href="/high-paying-remote-jobs/">high paying remote jobs</a> or <a href="/jobs/">all remote jobs</a>.</p>'}
<h2>Compare other salaries</h2>{nav}
{f'<p>Hourly instead? See <a href="{hourly_path(hr)}">${hr} an hour is how much a year</a>.</p>' if hr in HOURLY_RANGE else ''}
<section class="faq"><h2>FAQ</h2>{faq_html}</section></article>"""
        b.write(path, body, f"{money(y)} a Year Is How Much an Hour? ({year}) | {b.BRAND}",
                f"{money(y)} a year is about {money2(h)} an hour, {money(y / 12)} a month and {money(y / 26)} bi-weekly. See remote jobs paying around {money(y)}.",
                [b.crumbs([("Home", "/"), ("Salary calculator", "/tools/hourly-to-salary-calculator/"), (f"{money(y)} a year", path)]),
                 {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
                     {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}])
        urls.append(path)
        b.LASTMOD[path] = b.TODAY.replace(day=1).isoformat()
    return urls


# ================================================================== round 2: features big boards lack
import json as _json
import urllib.request as _ur

COMPANY_PAGES = {}   # company name -> path
SKILL_PAGES = {}     # skill slug -> (name, path, count)
MIN_COMPANY = 3
MIN_SKILL = 5
BUILD_TIME = datetime.datetime.utcnow().replace(microsecond=0)

SKILLS = [
    ("excel", "Excel", r"\bexcel\b|spreadsheet"), ("zendesk", "Zendesk", r"zendesk"),
    ("salesforce", "Salesforce", r"salesforce"), ("hubspot", "HubSpot", r"hubspot"),
    ("quickbooks", "QuickBooks", r"quickbooks"), ("shopify", "Shopify", r"shopify"),
    ("google-ads", "Google Ads", r"google ads|adwords|\bppc\b"), ("seo", "SEO", r"\bseo\b"),
    ("figma", "Figma", r"figma"), ("canva", "Canva", r"\bcanva\b"),
    ("python", "Python", r"\bpython\b"), ("javascript", "JavaScript", r"javascript|typescript|node\.?js"),
    ("react", "React", r"\breact\b"), ("sql", "SQL", r"\bsql\b"), ("aws", "AWS", r"\baws\b|amazon web services"),
    ("wordpress", "WordPress", r"wordpress"), ("jira", "Jira", r"\bjira\b"),
    ("spanish-speaking", "Spanish Speaking", r"spanish|bilingual \(?spanish|español"),
    ("french-speaking", "French Speaking", r"\bfrench[- ]speaking|fluent (in )?french|bilingual french"),
    ("german-speaking", "German Speaking", r"\bgerman[- ]speaking|fluent (in )?german|\(german\)|- german\b"),
    ("portuguese-speaking", "Portuguese Speaking", r"portuguese"),
    ("social-media", "Social Media", r"social media|instagram|tiktok"),
    ("video-editing", "Video Editing", r"video edit|premiere pro|after effects"),
    ("bookkeeping", "Bookkeeping", r"bookkeep"),
]

TZ_RULES = [
    (r"\b(est|edt|eastern time|eastern standard|us eastern|et time zone)\b", "America/New_York", "US Eastern"),
    (r"\b(pst|pdt|pacific time|pacific standard|us pacific)\b", "America/Los_Angeles", "US Pacific"),
    (r"\b(cst|cdt|central time|us central)\b", "America/Chicago", "US Central"),
    (r"\b(mst|mdt|mountain time)\b", "America/Denver", "US Mountain"),
    (r"\b(aest|aedt|sydney time|australian eastern)\b", "Australia/Sydney", "Australian Eastern"),
    (r"\b(cet|cest|central european)\b", "Europe/Berlin", "Central European"),
    (r"\b(gmt|bst|uk hours|uk time)\b", "Europe/London", "UK"),
]


def _tz_for(j):
    txt = (j["title"] + " " + (j.get("location_text") or "") + " " + j["_text"][:4000]).lower()
    for rx, tz, label in TZ_RULES:
        if re.search(rx, txt):
            return tz, label, True
    cs = set(j.get("applicant_countries") or [])
    if cs and cs <= {"United States"}:
        return "America/New_York", "US Eastern", False
    if cs and cs <= {"United Kingdom"}:
        return "Europe/London", "UK", False
    return "", "", False


def is_beginner(j):
    return bool(COLLECTIONS[0][3](j) or COLLECTIONS[6][3](j))  # entry level or no degree


def company_slug(name):
    return b.slugify(name)


def prepare2(jobs):
    """Called from prepare(): flags used by cards, job pages and local.js."""
    cc = Counter(j["company"] for j in jobs)
    for name, n in cc.items():
        if n >= MIN_COMPANY:
            COMPANY_PAGES[name] = f"/companies/{company_slug(name)}/"
    for slug, name, rx in SKILLS:
        r = re.compile(rx, re.I)
        n = sum(1 for j in jobs if r.search(j["title"] + " " + j["_text"][:6000]))
        if n >= MIN_SKILL:
            SKILL_PAGES[slug] = (name, f"/remote-{slug}-jobs/", n)
    for j in jobs:
        j["beginner"] = is_beginner(j)
        j["tz"], j["tz_label"], j["tz_exact"] = _tz_for(j)


def data_attrs(j):
    """Attributes local.js reads to show 'open to your country', local hours and local pay."""
    cs = "|".join(j.get("applicant_countries") or [])
    a = j.get("_annual") or ""
    return (f' data-c="{esc(cs)}"' + (' data-ww="1"' if j.get("worldwide") else "") +
            (f' data-pay="{int(a)}"' if a else ""))


def job_extra_rows(j):
    """Extra rows for the Job details box (filled in by local.js in the visitor's browser)."""
    rows = '<dt>Can I apply from my country?</dt><dd class="elig" data-c="{}"{}>{}</dd>'.format(
        esc("|".join(j.get("applicant_countries") or [])), ' data-ww="1"' if j.get("worldwide") else "",
        "Open worldwide" if j.get("worldwide") else esc(", ".join(j.get("applicant_countries") or []) or "Not stated by the employer"))
    if j.get("tz"):
        rows += (f'<dt>Working hours in your time</dt><dd class="localhours" data-tz="{j["tz"]}" data-exact="{1 if j["tz_exact"] else 0}" '
                 f'data-label="{esc(j["tz_label"])}">9 AM – 5 PM {esc(j["tz_label"])} time{"" if j["tz_exact"] else " (estimated)"}</dd>')
    if j.get("_annual"):
        rows += f'<dt>Pay in your currency</dt><dd class="localpay" data-pay="{int(j["_annual"])}">About {money(j["_annual"])} a year</dd>'
    if j.get("beginner"):
        rows += '<dt>Good for beginners?</dt><dd>Yes: the listing mentions entry-level, training or no degree needed</dd>'
    return rows


def source_line(j):
    host = re.sub(r"^https?://([^/]+).*$", r"\1", j.get("apply_url") or "")
    co = COMPANY_PAGES.get(j["company"])
    co_link = f' &middot; <a href="{co}">All {esc(j["company"])} remote jobs</a>' if co else ""
    return (f'<p class="source-line">✔ Source: {esc(j["company"])}&#39;s own job board ({esc(host)}) &middot; '
            f'<span class="checked" data-t="{BUILD_TIME.isoformat()}Z">Checked {BUILD_TIME.strftime("%b %d, %H:%M")} UTC</span>{co_link}</p>')


def fetch_fx():
    """Exchange rates for 'pay in your currency'. If the rate service is down, the feature just hides itself."""
    try:
        with _ur.urlopen("https://open.er-api.com/v6/latest/USD", timeout=12) as r:
            d = _json.loads(r.read().decode())
        if d.get("result") == "success":
            return {k: v for k, v in d["rates"].items()}
    except Exception:  # noqa
        pass
    return {}


def build_companies():
    urls = []
    names = cat_names()
    rows = ""
    for name, path in sorted(COMPANY_PAGES.items(), key=lambda kv: kv[0].lower()):
        cj = [j for j in JOBS if j["company"] == name]
        cats = Counter(c for j in cj for c in j["cats"]).most_common(3)
        ctr = Counter(c for j in cj for c in (j.get("applicant_countries") or [])).most_common(6)
        pays = sorted(j["_annual"] for j in cj if j.get("_annual"))
        beg = sum(1 for j in cj if j.get("beginner"))
        ww = sum(1 for j in cj if j.get("worldwide"))
        hosts = Counter(re.sub(r"^https?://([^/]+).*$", r"\1", j.get("apply_url") or "") for j in cj).most_common(1)
        facts = [f"<dt>Open remote jobs</dt><dd>{len(cj):,}</dd>"]
        if cats:
            facts.append("<dt>Hires most for</dt><dd>" + ", ".join(f'<a href="/{c}/">{esc(names[c])}</a>' for c, _ in cats) + "</dd>")
        if ctr:
            facts.append("<dt>Hires people in</dt><dd>" + ", ".join(
                (f'<a href="{COUNTRY_PAGES[c][0]}">{esc(c)}</a>' if c in COUNTRY_PAGES else esc(c)) for c, _ in ctr) +
                (" and more" if len(set(c for j in cj for c in (j.get("applicant_countries") or []))) > 6 else "") + "</dd>")
        if ww:
            facts.append(f"<dt>Work-from-anywhere jobs</dt><dd>{ww}</dd>")
        if len(pays) >= 2:
            facts.append(f"<dt>Published pay range</dt><dd>{money(pays[0])} – {money(pays[-1])} a year ({len(pays)} jobs list pay)</dd>")
        if beg:
            facts.append(f"<dt>Beginner-friendly jobs</dt><dd>{beg}</dd>")
        if hosts and hosts[0][0]:
            facts.append(f"<dt>Applications go to</dt><dd>{esc(hosts[0][0])} (the company's own job board)</dd>")
        newest = max(j["date_posted"] for j in cj)
        intro = (f'<p class="lead">{esc(name)} has {len(cj):,} open remote job{"s" if len(cj) != 1 else ""} right now. '
                 f'The newest was posted on {datetime.date.fromisoformat(newest).strftime("%B %d, %Y")}. Every job below links to '
                 f'{esc(name)}&#39;s own application page.</p><section class="facts"><h2>{esc(name)} at a glance</h2><dl>{"".join(facts)}</dl></section>')
        urls += b.paged(path, cj, f"{name} Remote Jobs",
                        f"{len(cj):,} remote jobs at {name}: countries they hire from, pay ranges and direct application links. Updated daily.",
                        intro, f"{name} Remote Jobs",
                        '<section class="wrap"><h2>More companies hiring remotely</h2>' + pills(
                            [(n, p) for n, p in sorted(COMPANY_PAGES.items(), key=lambda kv: -sum(1 for j in JOBS if j["company"] == kv[0]))
                             if n != name][:24] + [("All companies", "/companies/")]) + "</section>")
        rows += f'<tr><td><a href="{path}">{esc(name)}</a></td><td>{len(cj)}</td><td>{esc(", ".join(names[c] for c, _ in cats[:2]))}</td><td>{ww or "–"}</td></tr>'
    if COMPANY_PAGES:
        b.write("/companies/", f"""<section class="hero hero-small"><div class="wrap"><nav class="crumbs"><a href="/">Home</a> / Companies</nav>
<h1>Companies Hiring Remotely</h1><p class="lead">{len(COMPANY_PAGES)} companies with open remote jobs right now, taken from their own career pages. Pick a company to see every open role, the countries it hires from and its published pay.</p></div></section>
{b.AD_LEADER}<section class="wrap"><div class="table-wrap"><table class="data-table"><thead><tr><th>Company</th><th>Open jobs</th><th>Hires most for</th><th>Work from anywhere</th></tr></thead><tbody>{rows}</tbody></table></div></section>{b.AD_BOX}""",
                f"Companies Hiring Remotely Right Now ({b.TODAY.strftime('%b %Y')}) | {b.BRAND}",
                f"{len(COMPANY_PAGES)} companies with open remote jobs: see who is hiring, for which roles and from which countries.",
                [b.crumbs([("Home", "/"), ("Companies", "/companies/")])])
        b.LASTMOD["/companies/"] = b.TODAY.isoformat()
        urls.append("/companies/")
    return urls


def build_skills():
    urls = []
    for slug, name, rx in SKILLS:
        if slug not in SKILL_PAGES:
            continue
        r = re.compile(rx, re.I)
        sj = [j for j in JOBS if r.search(j["title"] + " " + j["_text"][:6000])]
        cos = Counter(j["company"] for j in sj).most_common(5)
        cats = Counter(c for j in sj for c in j["cats"]).most_common(4)
        names = cat_names()
        title = f"Remote {name} Jobs"
        intro = (f'<p class="lead">{len(sj):,} remote jobs that mention {esc(name)}, from employers such as {esc(", ".join(c for c, _ in cos))}. '
                 + ("Most are in " + ", ".join(f'<a href="/{c}/">{esc(names[c].lower())}</a>' for c, _ in cats) + ". " if cats else "")
                 + f'Showing {esc(name)} on your resume, with a real example of how you used it, helps you stand out for these roles.</p>')
        others = pills([(n, p) for s, (n, p, _) in SKILL_PAGES.items() if s != slug][:20])
        urls += b.paged(f"/remote-{slug}-jobs/", sj, title,
                        f"{len(sj):,} remote jobs that need {name}. Real openings from company career pages, updated daily.",
                        intro, title, f'<section class="wrap"><h2>Browse by skill</h2>{others}</section>')
    return urls


LOCAL_JS = r"""(function(){
var TZC={'Asia/Dhaka':'Bangladesh','Asia/Manila':'Philippines','Asia/Kolkata':'India','Asia/Calcutta':'India','Asia/Karachi':'Pakistan','Africa/Lagos':'Nigeria','Africa/Nairobi':'Kenya','Africa/Johannesburg':'South Africa','Africa/Cairo':'Egypt','Africa/Accra':'Ghana','Africa/Casablanca':'Morocco','Asia/Jakarta':'Indonesia','Asia/Kuala_Lumpur':'Malaysia','Asia/Ho_Chi_Minh':'Vietnam','Asia/Saigon':'Vietnam','Asia/Bangkok':'Thailand','Asia/Singapore':'Singapore','Asia/Colombo':'Sri Lanka','Asia/Kathmandu':'Nepal','Asia/Dubai':'United Arab Emirates','Asia/Riyadh':'Saudi Arabia','Asia/Tokyo':'Japan','Asia/Seoul':'South Korea','Asia/Taipei':'Taiwan','Asia/Jerusalem':'Israel','Europe/Istanbul':'Turkey','Europe/London':'United Kingdom','Europe/Dublin':'Ireland','Europe/Berlin':'Germany','Europe/Paris':'France','Europe/Madrid':'Spain','Europe/Rome':'Italy','Europe/Amsterdam':'Netherlands','Europe/Warsaw':'Poland','Europe/Lisbon':'Portugal','Europe/Bucharest':'Romania','Europe/Kiev':'Ukraine','Europe/Kyiv':'Ukraine','Europe/Stockholm':'Sweden','Europe/Athens':'Greece','America/New_York':'United States','America/Chicago':'United States','America/Denver':'United States','America/Phoenix':'United States','America/Los_Angeles':'United States','America/Anchorage':'United States','Pacific/Honolulu':'United States','America/Detroit':'United States','America/Toronto':'Canada','America/Vancouver':'Canada','America/Edmonton':'Canada','America/Winnipeg':'Canada','America/Halifax':'Canada','America/Mexico_City':'Mexico','America/Bogota':'Colombia','America/Lima':'Peru','America/Sao_Paulo':'Brazil','America/Argentina/Buenos_Aires':'Argentina','America/Buenos_Aires':'Argentina','America/Santiago':'Chile','America/Costa_Rica':'Costa Rica','America/Santo_Domingo':'Dominican Republic','America/Jamaica':'Jamaica','America/Guatemala':'Guatemala','America/Montevideo':'Uruguay','Australia/Sydney':'Australia','Australia/Melbourne':'Australia','Australia/Brisbane':'Australia','Australia/Perth':'Australia','Pacific/Auckland':'New Zealand'};
var CUR={'Bangladesh':['BDT','৳'],'Philippines':['PHP','₱'],'India':['INR','₹'],'Pakistan':['PKR','Rs '],'Nigeria':['NGN','₦'],'Kenya':['KES','KSh '],'South Africa':['ZAR','R'],'Egypt':['EGP','E£'],'Ghana':['GHS','GH₵'],'Indonesia':['IDR','Rp '],'Malaysia':['MYR','RM '],'Vietnam':['VND','₫'],'Thailand':['THB','฿'],'Sri Lanka':['LKR','Rs '],'Nepal':['NPR','Rs '],'Brazil':['BRL','R$'],'Mexico':['MXN','MX$'],'Colombia':['COP','COL$'],'Argentina':['ARS','AR$'],'Peru':['PEN','S/ '],'Chile':['CLP','CLP$'],'United Kingdom':['GBP','£'],'Germany':['EUR','€'],'France':['EUR','€'],'Spain':['EUR','€'],'Italy':['EUR','€'],'Netherlands':['EUR','€'],'Ireland':['EUR','€'],'Portugal':['EUR','€'],'Poland':['PLN','zł '],'Romania':['RON','lei '],'Turkey':['TRY','₺'],'Ukraine':['UAH','₴'],'Canada':['CAD','CA$'],'Australia':['AUD','A$'],'New Zealand':['NZD','NZ$'],'Japan':['JPY','¥'],'Singapore':['SGD','S$'],'United Arab Emirates':['AED','AED '],'Saudi Arabia':['SAR','SAR '],'Morocco':['MAD','MAD ']};
var store={get:function(){try{return localStorage.getItem('rjCountry');}catch(e){return null;}},set:function(v){try{localStorage.setItem('rjCountry',v);}catch(e){}}};
var myTz='';try{myTz=Intl.DateTimeFormat().resolvedOptions().timeZone||'';}catch(e){}
var me=store.get()||TZC[myTz]||'';
var fx=null;
function inList(el){var c=(el.getAttribute('data-c')||'').split('|').filter(Boolean);return{ww:el.getAttribute('data-ww')==='1',list:c,ok:el.getAttribute('data-ww')==='1'||c.indexOf(me)>=0};}
function badges(){document.querySelectorAll('a.job[data-c]').forEach(function(a){var old=a.querySelector('.tag.elig-b');if(old)old.remove();if(!me)return;var r=inList(a),t=a.querySelector('.tags');if(!t)return;
 var s=document.createElement('span');if(r.ww){s.className='tag elig-b ok';s.textContent='✓ Open worldwide';}else if(!r.list.length){return;}else if(r.ok){s.className='tag elig-b ok';s.textContent='✓ Open to '+me;}else{s.className='tag elig-b no';s.textContent='Not open to '+me;}
 t.insertBefore(s,t.firstChild);});}
function bar(){var lists=document.querySelectorAll('.job-list');if(!lists.length)return;var first=lists[0];var cards=document.querySelectorAll('a.job[data-c]');if(!cards.length)return;
 var b=document.getElementById('ctryBar');if(!b){b=document.createElement('div');b.id='ctryBar';b.className='ctry-bar';first.parentNode.insertBefore(b,first);}
 var opts=Object.keys(CUR).concat(['United States']).filter(function(v,i,a){return a.indexOf(v)===i;}).sort();
 if(me&&opts.indexOf(me)<0)opts.unshift(me);
 var n=0;cards.forEach(function(a){if(inList(a).ok)n++;});
 b.innerHTML='<label>Your country: <select id="ctrySel"><option value="">Choose…</option>'+opts.map(function(o){return '<option'+(o===me?' selected':'')+'>'+o+'</option>';}).join('')+'</select></label>'+
 (me?'<span><b>'+n+'</b> of '+cards.length+' jobs on this page are open to '+me+'</span><label class="only"><input type="checkbox" id="ctryOnly"> Show only these</label>':'<span>Pick your country to see which jobs you can apply for.</span>');
 document.getElementById('ctrySel').onchange=function(){me=this.value;store.set(me);run();};
 var o=document.getElementById('ctryOnly');if(o)o.onchange=function(){var on=this.checked;cards.forEach(function(a){a.style.display=(on&&!inList(a).ok)?'none':'';});};}
function offset(tz){var d=new Date();var a=new Date(d.toLocaleString('en-US',{timeZone:tz}));var u=new Date(d.toLocaleString('en-US',{timeZone:'UTC'}));return (a-u)/3600000;}
function fmt(h){h=((h%24)+24)%24;var hh=Math.floor(h),mm=Math.round((h-hh)*60);if(mm===60){hh=(hh+1)%24;mm=0;}return (hh%12||12)+(mm?':'+(mm<10?'0':'')+mm:'')+' '+(hh>=12?'PM':'AM');}
function hours(){document.querySelectorAll('.localhours').forEach(function(el){var tz=el.getAttribute('data-tz');if(!tz||!myTz)return;var d;try{d=offset(myTz)-offset(tz);}catch(e){return;}
 var s=9+d,e=17+d,night=(((s%24)+24)%24)>=18||(((s%24)+24)%24)<5;
 el.innerHTML=fmt(s)+' – '+fmt(e)+' your time'+(night?' <b>(night shift for you)</b>':'')+'<br><small>Based on 9 AM – 5 PM '+el.getAttribute('data-label')+' time'+(el.getAttribute('data-exact')==='1'?'':' (estimated: the listing does not state hours)')+'</small>';});}
function pay(){if(!fx||!me||!CUR[me])return;var c=CUR[me],r=fx[c[0]];if(!r)return;document.querySelectorAll('.localpay').forEach(function(el){var y=+el.getAttribute('data-pay')*r;
 el.innerHTML='About '+c[1]+Math.round(y/12).toLocaleString()+' a month ('+c[1]+Math.round(y).toLocaleString()+' a year) if full-time, before tax<br><small>Converted from US dollars at today\'s rate</small>';});}
function elig(){document.querySelectorAll('dd.elig').forEach(function(el){if(!me)return;var r=inList(el);if(r.ww){el.innerHTML='<b class="ok">✓ Yes, open worldwide</b>';}else if(!r.list.length){return;}else if(r.ok){el.innerHTML='<b class="ok">✓ Yes, open to '+me+'</b><br><small>Hires in: '+r.list.join(', ')+'</small>';}else{el.innerHTML='<b class="no">✗ Not open to '+me+'</b><br><small>Hires in: '+r.list.join(', ')+'</small>';}});}
function checked(){document.querySelectorAll('.checked[data-t]').forEach(function(el){var t=new Date(el.getAttribute('data-t'));var h=Math.round((Date.now()-t)/3600000);if(h>=0&&h<200)el.textContent='Checked '+(h<1?'less than an hour':h+' hour'+(h===1?'':'s'))+' ago';});}
function run(){badges();bar();elig();hours();pay();checked();}
run();
fetch('/data/fx.json').then(function(r){return r.ok?r.json():null;}).then(function(d){fx=d;pay();}).catch(function(){});
})();"""

LOCAL_CSS = """
.tag.elig-b.ok{background:#dcfce7;color:#166534}.tag.elig-b.no{background:#fee2e2;color:#991b1b}
.ctry-bar{display:flex;flex-wrap:wrap;gap:.6rem 1.2rem;align-items:center;background:#fff;border:2px solid var(--border);border-radius:var(--radius);padding:.8rem 1rem;margin:0 0 1rem;font-size:.95rem}
.ctry-bar select{padding:.35rem .5rem;border:2px solid var(--border);border-radius:8px;font:inherit}
.ctry-bar .only{display:flex;gap:.35rem;align-items:center;cursor:pointer}
b.ok{color:#166534}b.no{color:#991b1b}
.source-line{font-size:.9rem;color:var(--muted);background:#f6f7fb;border-radius:10px;padding:.6rem .9rem;margin:.8rem 0}
.free-note{font-weight:600;color:var(--primary);margin-top:.6rem}
"""


def build_round2():
    import os
    urls = build_companies() + build_skills()
    os.makedirs(os.path.join(b.OUT, "data"), exist_ok=True)
    fx = fetch_fx()
    with open(os.path.join(b.OUT, "data", "fx.json"), "w") as f:
        _json.dump(fx, f)
    with open(os.path.join(b.OUT, "assets", "local.js"), "w") as f:
        f.write(LOCAL_JS)
    with open(os.path.join(b.OUT, "assets", "extra.css"), "a") as f:
        f.write(LOCAL_CSS)
    print(f"Companies: {len(COMPANY_PAGES)} pages, skills: {len(SKILL_PAGES)} pages, fx rates: {len(fx)}")
    return urls
