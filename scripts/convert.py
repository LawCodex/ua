#!/usr/bin/env python3
"""Convert the downloaded TXT texts (see ua_fetch.py) to Markdown files in the repository.

Usage: convert.py [--kmu] [--clean]
--clean removes generated Markdown files that no longer correspond to a selected document.
"""
import argparse
import datetime as dt
import email.utils
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

TYPE = {"konstytutsiia": "constitution", "kodeksy": "code", "zakony": "act",
        "postanovy-kmu": "resolution"}

ROMAN = r"[IVXLCDMІХ]+"
ORD = (r"(?i:перш|друг|трет|четверт|п'ят|п’ят|шост|сьом|восьм|дев'ят|дев’ят|десят|"
       r"одинадцят|дванадцят|тринадцят|чотирнадцят|п'ятнадцят|шістнадцят)\w*")
DESIG = rf"(?:{ROMAN}|\d+|{ORD})(?:[-–]?\s?(?:\d+|[А-ЯA-Z]{{1,2}}\b))?(?:\d)*"
KINDS = [  # (kind, regex for the keyword), from the highest level to the lowest
    ("chastyna", r"ЧАСТИНА|Частина"),
    ("knyha", r"КНИГА|Книга"),
    ("rozdil", r"РОЗДІЛ|Розділ|Р\s?о\s?з\s?д\s?і\s?л"),
    ("pidrozdil", r"ПІДРОЗДІЛ|Підрозділ"),
    ("hlava", r"ГЛАВА|Глава"),
    ("paragraf", r"§|ПАРАГРАФ|Параграф"),
]
KIND_RE = [(k, re.compile(rf"^({kw})\s*({DESIG})(?:\s*[.:]?\s+(.*)|\.?)$")) for k, kw in KINDS]
PART_RE = re.compile(r"^(ЗАГАЛЬНА|ОСОБЛИВА|СПЕЦІАЛЬНА)\s+ЧАСТИНА$")
ART_RE = re.compile(r"^(?:Стаття|СТАТТЯ)\s+(\d+(?:[-–]\d+)*)(?:\s*\.\s*|\s+|$)(.*)$")


def is_upperish(s):
    letters = [c for c in s if c.isalpha()]
    return bool(letters) and sum(c.isupper() for c in letters) / len(letters) > 0.8


def heading_rest_ok(rest):
    rest = rest.strip()
    if not rest:
        return True
    if is_upperish(rest):
        return True
    return rest[0].isupper() and not rest.endswith((".", ";", ":", ",")) and len(rest) < 250


def structural(line):
    """Return (kind, label, rest) if the line is a structural heading."""
    if len(line) > 300:
        return None
    if PART_RE.match(line):
        return ("chastyna", line, "")
    for kind, rx in KIND_RE:
        m = rx.match(line)
        if m:
            rest = (m.group(3) or "").strip()
            if kind == "chastyna" and not (rest == "" or is_upperish(rest)):
                return None  # "Частина перша статті 5 ..." is running text
            if not heading_rest_ok(rest):
                return None
            label = re.sub(r"\s+", " ", m.group(1) + " " + m.group(2)).strip()
            return (kind, label, rest)
    return None


def esc(s):
    s = s.replace("\\", "\\\\").replace("*", "\\*").replace("_", "\\_")
    s = re.sub(r"<(?=[A-Za-z/!?А-Яа-яІіЇїЄєҐґ])", r"\\<", s)
    s = re.sub(r"^([#>+\-=|`~])", r"\\\1", s)
    s = re.sub(r"^(\d+)([.)])(\s)", r"\1\\\2\3", s)  # keep "1." from becoming a renumbered list
    return s


def to_markdown_body(text):
    lines = [re.sub(r"[ \t ]+$", "", l) for l in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    lines = [l for l in lines if l.strip()]
    # pass 1: find structural lines, merge headings with their title line
    items = []  # (kind or None, text)
    i = 0
    in_quote = False  # inside text quoted by an amending provision ("... такого змісту: "Стаття 5. ...")
    while i < len(lines):
        l = lines[i].strip()
        odd = l.count('"') % 2 == 1 or l.count("«") != l.count("»")
        if in_quote:
            if odd:
                in_quote = False
            items.append((None, l))
            i += 1
            continue
        if odd and l[:1] in ('"', "«", "“"):
            in_quote = True
            items.append((None, l))
            i += 1
            continue
        st = structural(l)
        if st:
            kind, label, rest = st
            if not rest and not PART_RE.match(l):
                nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
                if (nxt and (not structural(nxt) or PART_RE.match(nxt)) and not ART_RE.match(nxt) and not nxt.startswith("{")
                        and len(nxt) < 300 and (is_upperish(nxt) or not nxt.endswith((".", ";", ":", ",")))):
                    rest = nxt
                    i += 1
            items.append((kind, label + (". " + rest if rest else "")))
            i += 1
            continue
        m = ART_RE.match(l)
        if m:
            num, rest = m.group(1), m.group(2).strip()
            if rest and rest.endswith((".", ";", ":")) and not rest.endswith("..."):
                items.append(("stattia", f"Стаття {num}"))
                items.append((None, rest))
            else:
                items.append(("stattia", f"Стаття {num}" + (". " + rest if rest else "")))
            i += 1
            continue
        items.append((None, l))
        i += 1
    present = [k for k, _ in KINDS if any(it[0] == k for it in items)]
    # article headings must fit in "######": with more than four levels above the article,
    # the highest levels share the "##" level
    off = max(0, len(present) - 4)
    level = {k: max(2, 2 + n - off) for n, k in enumerate(present)}
    level["stattia"] = 2 + len(present) - off
    out = []
    for kind, t in items:
        if kind is None:
            out.append(esc(t))
        else:
            lv = level[kind]
            t = esc(t)
            out.append("#" * lv + " " + t if lv <= 6 else f"**{t}**")
    return "\n\n".join(out) + "\n"


def yaml_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def iso(d):
    return f"{d[:4]}-{d[4:6]}-{d[6:8]}" if d and len(d) == 8 else ""


def doc_date(hdr):
    try:
        return email.utils.parsedate_to_datetime(hdr).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return ""


def out_path(cat, d):
    base = C.nreg_slug(d["nreg"])
    title = re.sub(r"^(Про|ПРО)\s+", "pro ", d["title"])
    name = (base + "-" + C.slug(title, 100 - len(base))).strip("-")
    year = C.adoption(d)[0][:4] or "unknown"
    if cat == "konstytutsiia":
        return os.path.join(cat, name + ".md")
    if cat == "kodeksy":
        return os.path.join(cat, name + ".md")
    if cat == "postanovy-kmu":
        # more than 1,000 resolutions a year: shard by number range
        num = re.match(r"\d+", d["nreg"])
        n = int(num.group()) if num else 0
        shard = f"{(n // 500) * 500:04d}-{(n // 500) * 500 + 499:04d}"
        return os.path.join(cat, year, shard, name + ".md")
    return os.path.join(cat, year, name + ".md")


def render(cat, d, text, side):
    date, num = C.adoption(d)
    last = doc_date(side.get("document_date")) or iso(d["datred"])
    status = "in_force" if d["status"] in C.IN_FORCE else ("repealed" if d["status"] == 1 else "unknown")
    fm = [
        "---",
        f"title: {yaml_str(d['title'])}",
        f"identifier: {yaml_str(d['nreg'])}",
    ]
    if num:
        fm.append(f"number: {yaml_str(num)}")
    fm += [
        f"dokid: {d['dokid']}",
        f"type: {TYPE[cat]}",
        "jurisdiction: ua",
        "language: uk",
    ]
    if iso(date):
        fm.append(f"date: {iso(date)}")
    if last:
        fm.append(f"last_amended: {last}")
    fm += [
        f"status: {status}",
        f"status_detail: {yaml_str(C.STATUS_NAMES.get(d['status'], ''))}",
        f"source: {yaml_str('https://zakon.rada.gov.ua/laws/show/' + d['nreg'])}",
        f"retrieved: {side.get('retrieved') or dt.date.today().isoformat()}",
        "---",
        "",
        f"# {esc(d['title'])}",
        "",
    ]
    return "\n".join(fm) + "\n" + to_markdown_body(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kmu", action="store_true")
    ap.add_argument("--clean", action="store_true")
    a = ap.parse_args()
    written, missing = set(), 0
    counts = {}
    for d in C.load_docs():
        cat = C.classify(d, a.kmu)
        if not cat:
            continue
        p = C.txt_path(d["nreg"])
        side = C.load_json(p[:-4] + ".json", None)
        if not side or not os.path.exists(p):
            missing += 1
            continue
        with open(p, encoding="utf-8", errors="replace") as f:
            text = f.read()
        rel = out_path(cat, d)
        dest = os.path.join(C.ROOT, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        md = render(cat, d, text, side)
        old = None
        if os.path.exists(dest):
            with open(dest, encoding="utf-8") as f:
                old = f.read()
        if old != md:
            with open(dest, "w", encoding="utf-8", newline="\n") as f:
                f.write(md)
        written.add(rel)
        counts[cat] = counts.get(cat, 0) + 1
    if a.clean:
        for cat in TYPE:
            top = os.path.join(C.ROOT, cat)
            for dp, _, fs in os.walk(top):
                for fn in fs:
                    rel = os.path.relpath(os.path.join(dp, fn), C.ROOT)
                    if fn.endswith(".md") and rel not in written:
                        os.remove(os.path.join(dp, fn))
    print("written:", counts, "not yet downloaded:", missing)


if __name__ == "__main__":
    main()
