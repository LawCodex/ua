"""Shared helpers for the Ukrainian LawCodex scripts.

Source: open-data API of the Verkhovna Rada legislation database ("Законодавство України"),
documented at https://data.rada.gov.ua/open/main/api/page3 .
"""
import json
import sys
import os
import re
import ssl
import time
import random
import zipfile

import requests
from requests.adapters import HTTPAdapter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.environ.get("UA_RAW", os.path.join(os.path.dirname(ROOT), "_raw", "ua"))
META_DIR = os.path.join(RAW, "meta")
TXT_DIR = os.path.join(RAW, "txt")

API = "https://data.rada.gov.ua"
# The API identifies anonymous open-data clients by the User-Agent "OpenData"; it must be exactly
# that string (a descriptive User-Agent such as "OpenData LawCodex/1.0 (...)" is refused with 403).
USER_AGENT = "OpenData"
# ... so the client identifies itself in separate headers
CLIENT_HEADERS = {
    "X-Client": "LawCodex/1.0 (+https://github.com/LawCodex/ua)",
    "From": "LawCodex (+https://github.com/LawCodex/ua)",
}

# Status codes (dictionary stan.txt)
STATUS_NAMES = {
    0: "Не визначено", 1: "Втратив чинність", 2: "Набирає чинності", 3: "Дію зупинено",
    4: "Дію відновлено", 5: "Чинний", 6: "Не набрав чинності",
    7: "Не застосовується на території України", 8: "Частково набрав чинності",
    9: "Втратив чинність крім окремих положень",
}
IN_FORCE = {2, 3, 4, 5, 8, 9}

# Document types (typ.txt) and issuing bodies (organs.txt) used for selection
T_LAW, T_KMU_POST, T_CODE_UA, T_CONST_UA = "1", "2", "21", "216"
ORG_VRU, ORG_KMU, ORG_VR_URSR = "1", "2", "600"

# Codes registered with type "Кодекс України" that are only historical partial editions
EXCLUDE = {"80731-10", "80732-10"}


class TLS12Adapter(HTTPAdapter):
    """The server's TLS stack is old and drops many OpenSSL 3 handshakes; cap at TLS 1.2."""

    @staticmethod
    def _ctx():
        ctx = ssl.create_default_context()
        ctx.maximum_version = ssl.TLSVersion.TLSv1_2
        return ctx

    def init_poolmanager(self, *a, **k):
        k["ssl_context"] = self._ctx()
        return super().init_poolmanager(*a, **k)

    def proxy_manager_for(self, *a, **k):
        k["ssl_context"] = self._ctx()
        return super().proxy_manager_for(*a, **k)


def session():
    s = requests.Session()
    s.mount("https://", TLS12Adapter())
    s.headers["User-Agent"] = USER_AGENT
    s.headers.update(CLIENT_HEADERS)
    return s


def get(s, url, headers=None, tries=12, timeout=180):
    """GET with retries/backoff on network errors and 5xx. Returns the Response (200/304/404...)."""
    last = None
    for i in range(tries):
        try:
            # never follow redirects: refusals redirect to zakon.rada.gov.ua, which robots.txt closes to bots
            r = s.get(url, headers=headers or {}, timeout=timeout, allow_redirects=False)
            if r.status_code in (429,) or r.status_code >= 500:
                last = f"HTTP {r.status_code}"
                time.sleep(min(600, 30 * (i + 1)))
                continue
            return r
        except requests.RequestException as e:  # TLS drops are frequent: retry
            last = str(e)[-120:]
            print(f"  retry {i+1} {time.strftime('%H:%M:%S')} {type(e).__name__}", file=sys.stderr, flush=True)
            # connection-level failures never reach the application; retry soon, then back off
            time.sleep(random.uniform(1, 3) if i < 4 else min(120, 10 * i))
    raise RuntimeError(f"giving up on {url}: {last}")


# ---------------------------------------------------------------- metadata

def load_docs():
    """Parse doc.txt (cards of all documents, TSV, cp1251) from the open-data set 'doc'."""
    path = os.path.join(META_DIR, "doc.txt")
    if not os.path.exists(path):
        with zipfile.ZipFile(os.path.join(META_DIR, "doc.zip")) as z:
            z.extract("doc.txt", META_DIR)
    docs = []
    with open(path, encoding="cp1251", errors="replace") as f:
        for line in f:
            p = line.rstrip("\r\n").split("\t")
            if len(p) < 9:
                continue
            dokid, nreg, nazva, status, types, organs, minjust, npix, datred = p[:9]
            orgs = []
            for o in organs.split(" "):
                if not o:
                    continue
                q = o.split(":")
                orgs.append({"ids": q[0].split("|"), "dates": q[1].split("|") if len(q) > 1 else [],
                             "nums": q[2].split("|") if len(q) > 2 else []})
            docs.append({
                "dokid": int(dokid), "nreg": nreg, "title": nazva.strip(),
                "status": int(status or 0), "types": types.split("|"), "organs": orgs,
                "datred": datred,
            })
    return docs


def first_org(d):
    return d["organs"][0]["ids"][0] if d["organs"] and d["organs"][0]["ids"] else ""


def adoption(d):
    o = d["organs"][0] if d["organs"] else None
    date = o["dates"][0] if o and o["dates"] else ""
    num = o["nums"][0] if o and o["nums"] else ""
    return date, num


def classify(d, include_kmu=False):
    """Return category for a selected document, else None."""
    if d["nreg"] in EXCLUDE or d["status"] not in IN_FORCE:
        return None
    t, org = d["types"], first_org(d)
    if T_CONST_UA in t and org == ORG_VRU:
        return "konstytutsiia"
    if T_CODE_UA in t and org in (ORG_VRU, ORG_VR_URSR):
        return "kodeksy"
    if T_LAW in t and org in (ORG_VRU, ORG_VR_URSR):
        return "zakony"
    if include_kmu and T_KMU_POST in t and org == ORG_KMU:
        return "postanovy-kmu"
    return None


# ---------------------------------------------------------------- names

_TR = {
    "а": "a", "б": "b", "в": "v", "г": "h", "ґ": "g", "д": "d", "е": "e", "є": "ie", "ж": "zh",
    "з": "z", "и": "y", "і": "i", "ї": "i", "й": "i", "к": "k", "л": "l", "м": "m", "н": "n",
    "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "shch", "ь": "", "ю": "iu", "я": "ia", "ё": "io", "ы": "y",
    "э": "e", "ъ": "", "'": "", "’": "", "ʼ": "",
}


def translit(s):
    """Ukrainian national transliteration (KMU resolution 55/2010), simplified to lowercase."""
    s = s.lower().replace("зг", "zgh")
    return "".join(_TR.get(c, c) for c in s)


def slug(s, maxlen=100):
    s = re.sub(r"[^a-z0-9]+", "-", translit(s)).strip("-")
    if len(s) > maxlen:
        s = s[:maxlen].rsplit("-", 1)[0]
    return s


def nreg_slug(nreg):
    return slug(nreg.replace("/", "-").replace("_", "-"), 40)


def txt_path(nreg):
    return os.path.join(TXT_DIR, nreg_slug(nreg) + ".txt")


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default
