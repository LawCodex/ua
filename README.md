# LawCodex — Ukraine (Україна)

Ukrainian legislation in force as Markdown, one file per act, in the official language
(Ukrainian). The texts are the current consolidated versions (*чинна редакція*) published by the
Verkhovna Rada of Ukraine in its legislation database
[«Законодавство України»](https://zakon.rada.gov.ua), retrieved through the database's official
[open-data API](https://data.rada.gov.ua/open/main/api/page3).

Retrieved: **@RETRIEVED@**. Read [Known gaps and limitations](#known-gaps-and-limitations) before
relying on these files.

## Contents

| Category | Directory | Files |
|---|---|---:|
| Constitution (*Конституція України*) | `konstytutsiia/` | @N_CONST@ |
| Codes (*кодекси*) | `kodeksy/` | @N_CODES@ |
| Laws (*закони*) | `zakony/<year>/` | @N_LAWS@ |
| **Total** | | **@N_TOTAL@** |

What is selected (from the document cards of the open-data set
[«Картки документів»](https://data.rada.gov.ua/open/data/doc)):

- **Constitution** — the Constitution of Ukraine of 28 June 1996 (`254к/96-вр`), as amended.
- **Codes** — every document of type *Кодекс України* adopted by the Verkhovna Rada of Ukraine (or
  the Verkhovna Rada of the Ukrainian SSR) whose status is in force. Two records that are only
  historical partial editions of the Code of Administrative Offences (`80731-10`, `80732-10`) are
  skipped. The Subsoil Code is registered under the title «Про надра» (`132/94-вр`).
- **Laws** — every document of type *Закон* issued by the Verkhovna Rada of Ukraine (or of the
  Ukrainian SSR) whose status is in force. This includes framework laws, laws ratifying
  international treaties, budget laws and amending laws (*«Про внесення змін до ...»*). An amending
  law keeps the status «Чинний» in the database after its changes are merged into the law it
  amends, so these laws are included: their own final and transitional provisions stay in force.
  Laws are grouped by the year of adoption.

"In force" means one of the database statuses: Чинний (in force), Набирає чинності (entering into
force), Частково набрав чинності (partly in force), Дію зупинено (suspended), Дію відновлено
(reinstated), Втратив чинність крім окремих положень (repealed except for some provisions). The
exact status is given in the `status_detail` field. Repealed acts, acts that never entered into
force, and acts marked «Не застосовується на території України» are not included.

## Not covered

- **Resolutions of the Cabinet of Ministers** (*постанови КМУ*) — about 24,300 are in force. At the
  pace the API asks for (one request every 5–7 s, at most 200 MB a day) they would take about
  five days to download, so they are not included in this snapshot. `scripts/ua_fetch.py --kmu`
  and `scripts/convert.py --kmu` fetch and convert them into `postanovy-kmu/<year>/<range>/`.
- Decrees and orders of the President, resolutions of the Verkhovna Rada (*постанови ВР*),
  ministerial orders, regulatory acts registered with the Ministry of Justice, decisions of the
  Constitutional Court, and international treaties that are not themselves Ukrainian laws.
- Laws of the USSR (`Органи влади СРСР`) and CIS model laws, which are listed in the database but
  were not enacted by the Ukrainian legislature.
- Earlier versions (*редакції*) of the acts: only the current version is stored. Git history will
  record later changes when the corpus is refreshed.

## Known gaps and limitations

The anonymous open-data access gives the texts in **plain text (TXT)** only. The HTML and JSON
formats of the API need a token issued to a registered IP address. Plain text loses some
formatting:

- **Superscripts are flattened.** Inserted articles and points are numbered with superscripts in
  Ukrainian law (article 149¹, point 16¹). In the TXT they become plain digits: «Стаття 1491»
  stands for *Article 149¹*, «161.» for *point 16¹*. The original numbering cannot be restored
  reliably from the text alone.
- **Tables are flattened.** In the TXT, each table cell is a separate line, with no row or column
  structure. Each cell becomes a paragraph here. Example: the excise rates table in Article 215 of
  the Tax Code.
- **Annexes published as images or separate files are missing.** Some annexes exist in the
  database only as scanned images or separate attachments. The budget laws are an example. In the
  text they appear only as a reference line in braces, such as `{ДОДАТКИ №№ 1-8 ...}`.
- **Headings are reconstructed** from the text by pattern matching. Book (*Книга*), part
  (*Частина*), section (*Розділ*), subsection (*Підрозділ*), chapter (*Глава*), paragraph (*§*)
  and article (*Стаття*) lines become Markdown headings. Some unusual layouts may be missed, and
  a quoted article inside an amending law may occasionally be marked as a heading.
- **Editorial notes stay in the text.** The database's notes in braces (`{Із змінами, внесеними
  згідно із Законом № ...}`, `{Статтю 5 виключено ...}`) are part of the official consolidated
  text and are kept as they are.
- Documents that the API did not serve are listed in the final report and in the
  `missing` count below, if any: @MISSING@

## Layout and file names

- `konstytutsiia/254k-96-vr-konstytutsiia-ukrainy.md`
- `kodeksy/<nreg>-<title>.md`, e.g. `kodeksy/435-15-tsyvilnyi-kodeks-ukrainy.md` (Civil Code).
- `zakony/<year>/<nreg>-<title>.md`, e.g. `zakony/1994/132-94-vr-pro-nadra.md`.

`<nreg>` is the database's system number of the document (*системний номер*, e.g. `254к/96-вр`,
`2341-14`, `5005-20`), transliterated to ASCII with `/` replaced by `-`. It is the identifier in
the official URL `https://zakon.rada.gov.ua/laws/show/<nreg>`. The suffix `-NN` of a law's
system number is the convocation (`-12` = 12th convocation of the Ukrainian SSR Rada, `-14` =
III convocation ... `-20` = IX convocation). `<title>` is the title transliterated with the
Ukrainian national system (Cabinet resolution 55/2010), cut to keep names under ~100 characters.

### File format

```markdown
---
title: "Про надра"                     # official title (Ukrainian)
identifier: "132/94-вр"                # system number (nreg) in the database
number: "132/94-ВР"                    # official number of the act
dokid: 14520                           # internal document id of the database
type: code                             # constitution | code | act
jurisdiction: ua
language: uk
date: 1994-07-27                       # adoption date
last_amended: 2026-01-01               # date of the consolidated version reproduced
status: in_force
status_detail: "Чинний"                # status in the database
source: "https://zakon.rada.gov.ua/laws/show/132/94-вр"
retrieved: 2026-10-12
---

# Про надра

...
```

The body is the official text line by line: one paragraph per line of the source, with
structural lines turned into headings. The heading levels follow the hierarchy that the act uses.
`#` is the title, then book / part / section / subsection / chapter / paragraph, with the article
at the deepest level. If an act has more levels than Markdown allows, articles are shown in **bold**.

## Sources

- Legislation database «Законодавство України», Verkhovna Rada of Ukraine:
  https://zakon.rada.gov.ua
- Open-data portal of the Verkhovna Rada: https://data.rada.gov.ua/open/data/zak
  - document cards (`doc.zip`, open-data set «Картки документів»):
    https://data.rada.gov.ua/ogd/zak/laws/data/csv/doc.zip
  - texts: `https://data.rada.gov.ua/laws/show/<nreg>.txt`
  - API documentation: https://data.rada.gov.ua/open/main/api/page3

## Licence

The open-data portal of the Verkhovna Rada publishes its data under the
[Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/)
licence. Its terms of use say: «Дані Порталу є доступними для їх подальшого вільного використання
та поширення ... з обов'язковим посиланням на джерело отримання такої інформації». In other words,
the data may be freely used and redistributed, including commercially, provided the source is
cited. Separately, Article 8 of the Law of Ukraine «Про авторське право і суміжні права» excludes
official documents such as laws from copyright.

Source: Verkhovna Rada of Ukraine, database «Законодавство України» (zakon.rada.gov.ua), via the
open-data portal data.rada.gov.ua.

## Regenerating

```sh
pip install -r scripts/requirements.txt
python scripts/ua_fetch.py          # downloads cards + texts into ../_raw/ua (resumable)
python scripts/convert.py --clean   # writes the Markdown files
# Cabinet resolutions as well:
python scripts/ua_fetch.py --kmu && python scripts/convert.py --kmu --clean
# later refresh of already downloaded texts (uses If-Modified-Since):
python scripts/ua_fetch.py --refresh
```

How the scripts follow the API rules:

- They send the User-Agent `OpenData`, the token the API requires for anonymous access. The
  server refuses (HTTP 403) any other User-Agent, including a descriptive one that contains the
  token.
- They wait a random 5–7 s between requests and use a single connection, as the documentation
  asks.
- They stay under the 200 MB/day anonymous limit: the downloaded bytes are counted per Kyiv
  calendar day, and the script sleeps until the next day once 190 MB is reached.
- They never call the token or limits endpoints.

The server's TLS endpoint often drops connections. The scripts cap TLS at 1.2 and retry with
backoff.

`robots.txt` on `data.rada.gov.ua` and `zakon.rada.gov.ua` disallows generic crawlers. These
scripts do not crawl web pages. They only use the documented open-data API endpoints, which the
Rada publishes for automated access («Доступ до API відбувається анонімно без обмежень», within
the limits above).
