"""Blog posts: built-in guides + any Markdown files in the posts/ folder,
with automatic internal links between posts, categories and jobs."""
import datetime, html, os, re
from blog_posts import POSTS as BUILTIN

BUILTIN_META = {
    "how-to-spot-remote-job-scams": ("", "remote job scams"),
    "remote-data-entry-jobs-guide": ("remote-data-entry-jobs", "data entry guide"),
    "remote-customer-service-jobs-guide": ("remote-customer-service-jobs", "customer service guide"),
    "remote-job-resume-tips": ("", "resume for remote jobs"),
}


# ------------------------------------------------------------------ Markdown -> HTML
def _inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", lambda m: f'<a href="{html.escape(m.group(2))}">{m.group(1)}</a>', t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?!\w)", r"<em>\1</em>", t)
    return t


def md_to_html(md):
    out, para, lst = [], [], None

    def flush():
        nonlocal para, lst
        if para:
            out.append("<p>" + _inline(" ".join(para)) + "</p>")
            para = []
        if lst:
            out.append(f"<{lst[0]}>" + "".join(f"<li>{_inline(i)}</li>" for i in lst[1]) + f"</{lst[0]}>")
            lst = None

    for line in md.splitlines():
        s = line.strip()
        if not s:
            flush(); continue
        m = re.match(r"^(#{2,4})\s+(.*)", s)
        if m:
            flush(); n = len(m.group(1)); out.append(f"<h{n}>{_inline(m.group(2))}</h{n}>"); continue
        if s.startswith("# "):
            continue  # the title comes from the front matter
        m = re.match(r"^[-*]\s+(.*)", s) or re.match(r"^\d+[.)]\s+(.*)", s)
        if m:
            kind = "ul" if s[0] in "-*" else "ol"
            if para: flush()
            if lst and lst[0] != kind: flush()
            lst = lst or (kind, [])
            lst[1].append(m.group(1)); continue
        if lst: flush()
        para.append(s)
    flush()
    return "\n".join(out)


def _front_matter(text):
    meta, body = {}, text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            for line in parts[1].splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip().lower()] = v.strip().strip('"').strip("'")
            body = parts[2]
    return meta, body


def load_posts(folder="posts", categories=()):
    """categories: list of (slug, name, short, ...) used to resolve 'category:' values."""
    lookup = {}
    for c in categories:
        for key in (c[0], c[1], c[2]):
            lookup[key.lower()] = c[0]
    posts = []
    for p in BUILTIN:
        cat, kw = BUILTIN_META.get(p["slug"], ("", ""))
        posts.append({**p, "cat": cat, "keyword": kw})
    if os.path.isdir(folder):
        for f in sorted(os.listdir(folder)):
            if not f.endswith((".md", ".markdown", ".txt")) or f.startswith(("_", ".")):
                continue
            meta, body = _front_matter(open(os.path.join(folder, f), encoding="utf-8").read())
            title = meta.get("title") or f.rsplit(".", 1)[0].replace("-", " ").title()
            slug = re.sub(r"[^a-z0-9]+", "-", (meta.get("slug") or f.rsplit(".", 1)[0]).lower()).strip("-")
            date = meta.get("date") or datetime.date.today().isoformat()
            if date > datetime.date.today().isoformat():
                continue  # scheduled post: appears on its date
            posts = [x for x in posts if x["slug"] != slug]
            posts.append({
                "slug": slug, "title": title,
                "desc": meta.get("description") or re.sub(r"\s+", " ", re.sub(r"[#*\[\]()>-]", " ", body)).strip()[:155],
                "date": date, "body": md_to_html(body),
                "cat": lookup.get((meta.get("category") or "").lower(), ""),
                "keyword": (meta.get("keyword") or "").lower(),
            })
    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


# ------------------------------------------------------------------ internal links
def autolink(body, phrases, self_url="", max_links=8):
    """Turn the first mention of each phrase into a link.
    phrases: list of (phrase, url). Skips headings, existing links and links to the page itself."""
    already = set(re.findall(r'href="([^"]+)"', body))
    todo = sorted({(p.lower(), u) for p, u in phrases if p and u != self_url and u not in already},
                  key=lambda x: -len(x[0]))
    state = {"used": set(), "count": 0}

    def link_text(text):
        if state["count"] >= max_links:
            return text
        for phrase, url in todo:
            if url in state["used"]:
                continue
            m = re.search(r"(?<![\w-])" + re.escape(phrase) + r"(?![\w-])", text, re.I)
            if m:
                state["used"].add(url); state["count"] += 1
                return (link_text(text[:m.start()]) + f'<a href="{url}">{m.group(0)}</a>'
                        + link_text(text[m.end():]))
        return text

    parts, depth = re.split(r"(<[^>]+>)", body), 0
    for i, part in enumerate(parts):
        if part.startswith("<"):
            tag = re.match(r"</?\s*(\w+)", part)
            if tag and tag.group(1).lower() in ("a", "h1", "h2", "h3", "h4"):
                depth += -1 if part.startswith("</") else 1
        elif depth <= 0 and part.strip():
            parts[i] = link_text(part)
    return "".join(parts)


def related_posts(post, posts, n=4):
    words = set(re.findall(r"[a-z]{4,}", (post["title"] + " " + post.get("keyword", "")).lower()))

    def score(o):
        s = 3 if post.get("cat") and o.get("cat") == post["cat"] else 0
        return s + len(words & set(re.findall(r"[a-z]{4,}", o["title"].lower())))
    others = [o for o in posts if o["slug"] != post["slug"]]
    return sorted(others, key=lambda o: (-score(o), o["date"]), reverse=False)[:n]
