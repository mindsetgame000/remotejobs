"""Google Indexing API (for JobPosting pages) without extra libraries.

Needs the environment variable GOOGLE_INDEXING_KEY = the full JSON key of a
Google Cloud service account that is an Owner of the site in Search Console.
"""
import base64, hashlib, json, os, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

SCOPE = "https://www.googleapis.com/auth/indexing"
PER_BUILD = int(os.environ.get("GOOGLE_INDEXING_LIMIT", "90"))  # site builds twice a day; Google allows 200/day


# ---------------- tiny DER reader + RSA (PKCS#1 v1.5, SHA-256) ----------------
def _der(b, i):
    tag = b[i]; i += 1
    ln = b[i]; i += 1
    if ln & 0x80:
        n = ln & 0x7F
        ln = int.from_bytes(b[i:i + n], "big"); i += n
    return tag, b[i:i + ln], i + ln


def _seq_items(b):
    out, i = [], 0
    while i < len(b):
        tag, val, i = _der(b, i)
        out.append((tag, val))
    return out


def _rsa_key(pem):
    body = "".join(l for l in pem.strip().splitlines() if "-----" not in l)
    der = base64.b64decode(body)
    _, top, _ = _der(der, 0)
    items = _seq_items(top)
    if items[1][0] == 0x30:            # PKCS#8 wrapper -> inner PKCS#1 key
        _, inner, _ = _der(items[2][1], 0)
        items = _seq_items(inner)
    n, e, d, p, q, dp, dq, qi = (int.from_bytes(v, "big") for _, v in items[1:9])
    return n, d, p, q, dp, dq, qi


def _sign(msg, key):
    n, d, p, q, dp, dq, qi = key
    k = (n.bit_length() + 7) // 8
    digest = bytes.fromhex("3031300d060960864801650304020105000420") + hashlib.sha256(msg).digest()
    em = b"\x00\x01" + b"\xff" * (k - len(digest) - 3) + b"\x00" + digest
    m = int.from_bytes(em, "big")
    m1, m2 = pow(m, dp, p), pow(m, dq, q)          # CRT for speed
    s = m2 + q * ((qi * (m1 - m2)) % p)
    return s.to_bytes(k, "big")


def _b64(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _token(info):
    now = int(time.time())
    head = _b64(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
    claim = _b64(json.dumps({"iss": info["client_email"], "scope": SCOPE, "aud": info["token_uri"],
                             "iat": now, "exp": now + 3600}).encode())
    sig = _b64(_sign(f"{head}.{claim}".encode(), _rsa_key(info["private_key"])))
    data = urllib.parse.urlencode({"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                                   "assertion": f"{head}.{claim}.{sig}"}).encode()
    with urllib.request.urlopen(urllib.request.Request(info["token_uri"], data=data), timeout=30) as r:
        return json.load(r)["access_token"]


def notify_google(urls):
    raw = os.environ.get("GOOGLE_INDEXING_KEY", "").strip()
    if not raw:
        print("Google Indexing API: off (GOOGLE_INDEXING_KEY not set)", file=sys.stderr)
        return
    try:
        info = json.loads(raw)
        info.setdefault("token_uri", "https://oauth2.googleapis.com/token")
        tok = _token(info)
    except Exception as e:  # noqa
        print(f"Google Indexing API: could not sign in ({e})", file=sys.stderr)
        return

    def send(u):
        req = urllib.request.Request("https://indexing.googleapis.com/v3/urlNotifications:publish",
                                     data=json.dumps({"url": u, "type": "URL_UPDATED"}).encode(),
                                     headers={"Content-Type": "application/json", "Authorization": f"Bearer {tok}"})
        try:
            urllib.request.urlopen(req, timeout=30).read()
            return "ok"
        except urllib.error.HTTPError as e:
            return f"{e.code}: {e.read()[:200].decode('utf-8', 'replace')}"
        except Exception as e:  # noqa
            return str(e)

    urls = urls[:PER_BUILD]
    with ThreadPoolExecutor(max_workers=4) as ex:
        results = list(ex.map(send, urls))
    ok = sum(r == "ok" for r in results)
    print(f"Google Indexing API: {ok}/{len(urls)} URLs sent", file=sys.stderr)
    for u, r in zip(urls, results):
        if r != "ok":
            print(f"  failed {u} -> {r}", file=sys.stderr)
            break  # one example is enough (usually permission or quota)
