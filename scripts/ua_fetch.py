#!/usr/bin/env python3
"""Download the current consolidated texts (TXT) of Ukrainian legislation in force.

Uses the official open-data API of the Verkhovna Rada "Законодавство України" database
(https://data.rada.gov.ua/open/main/api/page3), anonymous "OpenData" access:
  * document cards:  https://data.rada.gov.ua/ogd/zak/laws/data/csv/doc.zip  (open-data set "doc")
  * texts:           https://data.rada.gov.ua/laws/show/<nreg>.txt
The API asks for a random 5-7 s pause between requests and caps anonymous use at 200 MB/day;
both are honoured here (the byte budget is tracked per Kyiv calendar day).

Usage: ua_fetch.py [--kmu] [--refresh] [--only CATEGORY] [--limit N]
Raw files go to ../_raw/ua (override with UA_RAW).
"""
import argparse
import datetime as dt
import json
import os
import random
import sys
import time
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

DAILY_BUDGET = 190 * 1024 * 1024
BUDGET_FILE = os.path.join(C.RAW, "budget.json")
KYIV = dt.timezone(dt.timedelta(hours=3))  # EEST; a 1 h error is harmless for the budget


def kyiv_day():
    return dt.datetime.now(KYIV).strftime("%Y-%m-%d")


def charge(nbytes):
    b = C.load_json(BUDGET_FILE, {})
    day = kyiv_day()
    b[day] = b.get(day, 0) + nbytes
    with open(BUDGET_FILE, "w") as f:
        json.dump(b, f)
    if b[day] > DAILY_BUDGET:
        now = dt.datetime.now(KYIV)
        nxt = (now + dt.timedelta(days=1)).replace(hour=0, minute=10, second=0, microsecond=0)
        wait = (nxt - now).total_seconds()
        print(f"daily byte budget reached ({b[day]} B); sleeping {wait/3600:.1f} h", flush=True)
        time.sleep(wait)


def pause():
    time.sleep(random.uniform(5, 7))


def fetch_meta(s, refresh):
    os.makedirs(C.META_DIR, exist_ok=True)
    z = os.path.join(C.META_DIR, "doc.zip")
    if refresh or not os.path.exists(z) or time.time() - os.path.getmtime(z) > 86400:
        r = C.get(s, C.API + "/ogd/zak/laws/data/csv/doc.zip")
        r.raise_for_status()
        with open(z + ".part", "wb") as f:
            f.write(r.content)
        os.replace(z + ".part", z)
        t = os.path.join(C.META_DIR, "doc.txt")
        if os.path.exists(t):
            os.remove(t)
        charge(len(r.content))
        pause()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kmu", action="store_true", help="also fetch Cabinet of Ministers resolutions")
    ap.add_argument("--refresh", action="store_true", help="re-check cached texts (If-Modified-Since)")
    ap.add_argument("--only", help="konstytutsiia|kodeksy|zakony|postanovy-kmu")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    s = C.session()
    fetch_meta(s, a.refresh)
    os.makedirs(C.TXT_DIR, exist_ok=True)
    order = {"konstytutsiia": 0, "kodeksy": 1, "zakony": 2, "postanovy-kmu": 3}
    sel = []
    for d in C.load_docs():
        cat = C.classify(d, a.kmu)
        if cat and (not a.only or a.only == cat):
            sel.append((order[cat], -int(C.adoption(d)[0] or 0), d))
    sel.sort(key=lambda x: (x[0], x[1]))
    print(f"{len(sel)} documents selected", flush=True)

    missing = C.load_json(os.path.join(C.RAW, "missing.json"), {})
    n = 0
    bad = 0  # consecutive refusals: stop instead of hammering a server that blocks us
    for i, (_, _, d) in enumerate(sel):
        path = C.txt_path(d["nreg"])
        side = path[:-4] + ".json"
        meta = C.load_json(side, None)
        if meta and not a.refresh:
            continue
        if a.limit and n >= a.limit:
            break
        n += 1
        url = f"{C.API}/laws/show/{quote(d['nreg'], safe='/')}.txt"
        hdr = {}
        if meta and meta.get("last_modified") and os.path.exists(path):
            hdr["If-Modified-Since"] = meta["last_modified"]
        try:
            r = C.get(s, url, hdr)
        except RuntimeError as e:
            print("FAIL", d["nreg"], e, flush=True)
            pause()
            continue
        if r.status_code == 304:
            print(f"[{i+1}/{len(sel)}] {d['nreg']} not modified", flush=True)
        elif r.status_code == 200 and r.headers.get("Content-Type", "").startswith("text/plain"):
            with open(path + ".part", "wb") as f:
                f.write(r.content)
            os.replace(path + ".part", path)
            with open(side, "w", encoding="utf-8") as f:
                json.dump({"nreg": d["nreg"], "url": url,
                           "last_modified": r.headers.get("Last-Modified"),
                           "document_date": r.headers.get("DocumentDate"),
                           "retrieved": dt.date.today().isoformat()}, f, ensure_ascii=False)
            missing.pop(d["nreg"], None)
            bad = 0
            print(f"[{i+1}/{len(sel)}] {d['nreg']} {len(r.content)} B", flush=True)
            charge(len(r.content))
        else:
            missing[d["nreg"]] = f"HTTP {r.status_code} {r.headers.get('Content-Type')}"
            print(f"[{i+1}/{len(sel)}] {d['nreg']} MISSING {missing[d['nreg']]}", flush=True)
            with open(os.path.join(C.RAW, "missing.json"), "w", encoding="utf-8") as f:
                json.dump(missing, f, ensure_ascii=False, indent=1)
            charge(len(r.content))
            bad = bad + 1 if r.status_code != 404 else 0
            if bad >= 5:
                print("5 consecutive refusals: stopping", flush=True)
                break
        pause()
    print("done", flush=True)


if __name__ == "__main__":
    main()
