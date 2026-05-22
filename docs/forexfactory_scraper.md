# Forex Factory Crawler User Guide

## Overview

`forexfactory_crawler.py` is a command-line archiver for Forex Factory forum threads. It scrapes a thread page by page, extracts posts and media, saves a structured local archive, and provides offline reporting and export tools.

The crawler is designed for long forum threads where interruptions, duplicate pages, missing post blocks, cached HTML, and validation problems are likely. It includes resume support, page-level completion markers, raw HTML caching, validation checks, repair mode, image downloading, Markdown/HTML generation, top-user reporting, and filtered single-file exports.

The script currently identifies itself as version `0.3.9`.

---

## Main Capabilities

The crawler can:

- scrape a live Forex Factory thread from a URL;
- start from any page number;
- resume interrupted archive runs;
- reuse cached raw HTML unless fresh HTML is requested;
- optionally log in before scraping;
- extract post IDs, post numbers, authors, timestamps, body text, quotes, signatures, attachments, and images;
- validate pages against expected post numbers;
- retry weak page parses once with fresh HTML;
- repair selected pages in an existing archive;
- generate `thread.json`, `thread.md`, and `thread.html`;
- report the top 10 posters by post count;
- export filtered dark-mode HTML files;
- create AI-friendly HTML exports with images embedded as base64 where possible.

---

## Requirements

Use Python 3.10 or newer.

Install dependencies:

```bash
pip install requests beautifulsoup4 tqdm lxml
```

`lxml` is optional but recommended. If it is unavailable, the script falls back to Python's built-in `html.parser`.

Third-party packages used by the script:

- `requests`
- `beautifulsoup4`
- `tqdm`
- `lxml`, optional

---

## Running the Script

From the repository root:

```bash
python src/forexfactory_crawler.py [options]
```

Some older examples in the source comments refer to `ffactory.py`. In this repository, use:

```bash
python src/forexfactory_crawler.py
```

---

## Quick Start

### Scrape a full public thread

```bash
python src/forexfactory_crawler.py --url "https://www.forexfactory.com/thread/1190104-m1-countertrend-scalping-strategy"
```

### Test one page first

```bash
python src/forexfactory_crawler.py --url "THREAD_URL" --start-page 1 --max-pages 1 --debug
```

### Start from a specific page

```bash
python src/forexfactory_crawler.py --url "THREAD_URL" --start-page 101
```

### Limit pages for testing

```bash
python src/forexfactory_crawler.py --url "THREAD_URL" --start-page 1 --max-pages 5
```

### Force fresh HTML instead of cached HTML

```bash
python src/forexfactory_crawler.py --url "THREAD_URL" --force
```

### Disable resume and start exactly from the requested page

```bash
python src/forexfactory_crawler.py --url "THREAD_URL" --start-page 1 --no-resume
```

### Restart deep into a live thread with a page overlap

```bash
python src/forexfactory_crawler.py --url "THREAD_URL" --start-page 300 --overlap-start-pages 1
```

### Provide login credentials

```bash
python src/forexfactory_crawler.py --url "THREAD_URL" --username "YOUR_USER" --password "YOUR_PASS"
```

If credentials are omitted in live scrape mode, the script prompts for them. Press Enter to continue as a public guest.

---

## Operating Modes

The script chooses its mode from command-line flags.

| Mode | Trigger | Description |
|---|---|---|
| Live scrape | Default mode | Scrapes a live Forex Factory thread and builds or updates an archive. |
| Repair mode | `--repair-pages` or `--repair-validation-warnings` | Reprocesses selected archive pages and replaces those page records. |
| Top 10 report | `--top10` | Counts posts by author in an existing archive. |
| Single HTML export | `--export-single-html` | Creates a dark-mode HTML export from an existing archive. |
| AI HTML export | `--export-ai-html` | Creates a portable HTML export with local images embedded where possible. |

If multiple action flags are supplied, the script runs the first matching branch in this order:

1. `--top10`
2. `--export-single-html`
3. `--export-ai-html`
4. `--repair-pages` or `--repair-validation-warnings`
5. live scrape

---

## Command-Line Options

| Option | Applies to | Description |
|---|---|---|
| `--url` | live scrape, repair, offline modes | Full Forex Factory thread URL. The script normalizes it by removing `page=` and fragments. |
| `--thread-dir` | offline modes | Direct path to an existing archive folder. |
| `--start-page` | live scrape, repair metadata | Page number to start from. Defaults to `1` when repair or offline mode does not need prompting. |
| `--username` | live scrape, repair | Optional username or email for login. |
| `--password` | live scrape, repair | Optional password for login. |
| `--output-root` | all modes | Base output folder. Defaults to `thread_archive`. |
| `--max-pages` | live scrape | Safety limit for test or partial runs. |
| `--force` | live scrape, repair | Re-fetch cached raw HTML. In live mode it also prevents normal resume inference. |
| `--debug` | live scrape, repair | Prints detailed log output to the console as well as `scrape.log`. |
| `--no-resume` | live scrape | Ignores saved progress and starts exactly from `--start-page`. |
| `--overlap-start-pages` | live scrape | Rewinds the requested start page by this many pages when no better resume source exists. |
| `--repair-pages` | repair | Reprocesses page selectors such as `145` or `145,200-202`. |
| `--repair-validation-warnings` | repair | Reprocesses pages listed in archive validation warnings. |
| `--top10` | offline report | Reports the top 10 users by post count. |
| `--export-single-html` | offline export | Creates a dark-mode HTML export from `thread.json`. |
| `--users` | offline exports | Comma-separated author filter. |
| `--single-html-output` | single HTML export | Custom filename for `--export-single-html`. `.html` is added if missing. |
| `--export-ai-html` | offline export | Creates an AI-friendly HTML export with embedded images where possible. |
| `--ai-html-output` | AI HTML export | Custom filename for `--export-ai-html`. `.html` is added if missing. |
| `--pages` | offline exports | Page filter such as `145` or `145,200-202`. |
| `--posts` | offline exports | Post-number filter such as `2886` or `2886,3000-3050`. A leading `#` is allowed. |
| `--posts-file` | offline exports | Text file containing post numbers and/or ranges. |

---

## Archive Folder Structure

By default, the archive root is:

```text
thread_archive/
```

Each thread gets its own slug-based folder:

```text
thread_archive/<thread-slug>/
```

A typical archive contains:

```text
<thread archive>/
├── raw_html/
│   └── page_0001.html, page_0002.html, ...
├── posts/
│   ├── <post-id>.html
│   └── <post-id>.json
├── images/
│   └── downloaded post images
├── assets/
│   └── style.css
├── page_state/
│   └── page_0001.done.json, page_0002.done.json, ...
├── thread.json
├── thread.md
├── thread.html
├── scrape.log
├── resume_state.json
├── last_run_summary.json
├── repair_summary.json
├── top10_report.json
├── single_html_export_report.json
└── ai_html_export_report.json
```

Not every report file exists after every run. Report files are created by their matching modes.

| File or Folder | Purpose |
|---|---|
| `raw_html/` | Cached source HTML for each page. |
| `posts/` | Per-post raw HTML and JSON snapshots. |
| `images/` | Downloaded images from posts. |
| `assets/style.css` | CSS used by `thread.html`. |
| `page_state/` | Page completion markers with validation details. |
| `thread.json` | Canonical structured archive. |
| `thread.md` | Markdown export of all archived posts. |
| `thread.html` | Local dark-mode HTML export. |
| `scrape.log` | Detailed operational log. |
| `resume_state.json` | State used to continue interrupted runs. |
| `last_run_summary.json` | Summary of the latest live scrape. |
| `repair_summary.json` | Summary of latest repair run. |
| `top10_report.json` | Top poster report. |
| `single_html_export_report.json` | Single HTML export report. |
| `ai_html_export_report.json` | AI HTML export report. |

---

## Live Scrape Logic Flow

The default live scrape mode is implemented by `scrape_thread()`.

### 1. Input Collection

The script parses command-line arguments and calls `collect_inputs()`.

In live mode, missing values are requested interactively:

- full thread URL;
- start page, defaulting to `1`;
- username, optional;
- password, optional.

Offline modes avoid username/password prompts.

### 2. URL Normalisation

The URL is cleaned by `normalize_thread_url()`:

- whitespace is stripped;
- `page=` is removed from the query string;
- fragments are removed;
- trailing `?` is removed.

Per-page URLs are generated by `get_page_url()`:

- page 1 uses the base URL;
- page 2 and later add `?page=N`.

### 3. Output Setup

The script builds a thread slug from the URL, creates the archive directories, writes CSS assets, configures logging, and removes leftover `.part` files from previous interrupted runs.

### 4. HTTP Session and Optional Login

A `requests.Session()` is created with browser-like headers.

If username and password are supplied, the script attempts automatic form discovery:

1. load `https://www.forexfactory.com/`;
2. find a form containing a password input;
3. build a payload from all form inputs;
4. infer username and password field names;
5. submit credentials;
6. verify whether the returned page contains `logout` or `log out`.

If login cannot be discovered or verified, the script logs a warning and continues as a guest.

### 5. Resume Detection

Before scraping, existing posts are loaded from `thread.json`.

When resume is enabled and `--force` is not used, the start page is inferred in this order:

1. `resume_state.json` field `next_page`;
2. latest page marker under `page_state/` plus one;
3. latest page found in `thread.json` plus one;
4. latest cached HTML page under `raw_html/`;
5. requested start page adjusted by `--overlap-start-pages`;
6. requested `--start-page`.

`--no-resume` disables resume inference. `--force` also disables normal live resume inference because the scrape call passes `resume_enabled and not force`.

### 6. Progress and ETA

A `tqdm` progress bar displays page progress.

ETA uses:

- an initial estimate of 15 seconds per page;
- a rolling recent window;
- weighted recent average;
- recent median;
- historical average from `resume_state.json`, when available.

### 7. Page Fetching

For each page, the script:

1. builds the page URL;
2. maps it to `raw_html/page_XXXX.html`;
3. uses cached HTML unless forced;
4. otherwise downloads the page;
5. writes fetched HTML atomically.

Requests are retried up to 5 times with a 20-second timeout and exponential backoff capped at 8 seconds.

### 8. Page Parsing

BeautifulSoup parses the page using `lxml` if available, otherwise `html.parser`.

The parser extracts:

- thread title;
- detected last page;
- expected post numbers;
- post block candidates.

### 9. Post Block Detection

The scraper looks for Forex Factory post permalinks matching:

```text
/thread/post/<post-id>
```

Visible post number anchors must match labels such as:

```text
# 2886
```

For each anchor, the script walks up the DOM and scores possible parent containers. It rejects quote wrappers, blockquotes, tiny fragments, over-broad containers, and containers with the wrong post-anchor pattern.

On page 1, there is special logic to recover the opening post if it is not represented like later numbered posts.

### 10. Post Extraction

Each post record can include:

- `post_id`
- `post_number`
- `post_url`
- `page`
- `author`
- `timestamp`
- `text`
- `body_text`
- `signature_text`
- `attachment_labels`
- `image_urls`
- `images`
- `accepted`
- `validation_reasons`

The raw HTML is saved in per-post `.html` snapshots but omitted from `thread.json`.

### 11. Author Extraction

The script first tries CSS selectors such as `.author`, `.username`, `[class*='author']`, and `[class*='user']`.

If those fail, it scans links and short text strings while filtering common noise such as reply controls, navigation labels, post numbers, external links, and attachment links.

If no author is found, it uses `Unknown`.

### 12. Timestamp Extraction

The script tries date-related selectors first, then searches nearby text using regular expressions for Forex Factory-style timestamps.

If no timestamp is found, it uses `Unknown date`.

### 13. Body, Quote, Attachment, and Signature Handling

The script chooses the best content node from selectors such as `.message`, `.content`, `.post-content`, `.postbody`, and class-name matches containing `message` or `content`.

It then:

- preserves line breaks from `<br>` and block-level elements;
- normalizes whitespace;
- repairs common mojibake;
- removes metadata noise;
- keeps quote text with `> ` prefixes;
- removes Forex Factory quote-widget artefacts such as `Disliked` and `Ignored`;
- extracts attachment labels;
- strips attachment UI fragments from body text;
- separates signatures after `<hr>` or explicit signature containers;
- deduplicates signature lines.

### 14. Image Handling

Images are extracted from `<img>` tags and image-like links.

The script:

- normalizes `/attachment/image/.../thumbnail` URLs to the full image URL;
- skips avatars, smileys, emojis, icons, logos, sprites, blank images, spacers, and pixels;
- downloads accepted images into `images/`;
- reuses already downloaded files;
- stores local relative image paths on the post record.

### 15. Validation

Post validation checks for strong signals:

- post ID;
- post number;
- timestamp.

Posts may be rejected when they are empty, weakly identified, quote-like, or missing essential signals.

Page validation checks:

- expected labelled post count;
- accepted labelled post count;
- missing post numbers;
- page 1 opener;
- extra accepted posts without labels;
- rejected weak candidates;
- accepted posts with `Unknown date`.

If validation fails, the page is retried once using fresh HTML. If it still fails, the page is recorded in `validation_warning_pages`.

### 16. Saving Results

After each page, the script:

1. saves per-post snapshots;
2. downloads or reuses images;
3. merges new posts with existing posts;
4. sorts by page and post number;
5. writes `thread.json`;
6. regenerates `thread.md`;
7. regenerates `thread.html`;
8. writes a page marker;
9. updates `resume_state.json`.

Writes are atomic: data is written to `.part` files and then moved into place.

### 17. Stop Conditions

The live scrape stops when:

- `--max-pages` is reached;
- no post blocks are found;
- the first post repeats from the previous page, preventing loops;
- the detected last page is reached;
- no new posts are found after the first page of the run;
- the user interrupts with Ctrl+C.

On interruption, the script preserves the last fully committed page in resume state.

---

## Repair Mode

Repair mode reprocesses selected pages inside an existing archive.

### Repair one page

```bash
python src/forexfactory_crawler.py --url "THREAD_URL" --output-root thread_archive --repair-pages 145
```

### Repair multiple pages

```bash
python src/forexfactory_crawler.py --url "THREAD_URL" --output-root thread_archive --repair-pages 145,200-202
```

### Repair pages listed in validation warnings

```bash
python src/forexfactory_crawler.py --url "THREAD_URL" --output-root thread_archive --repair-validation-warnings
```

Repair mode:

1. resolves the archive folder;
2. loads existing `thread.json` and resume state;
3. selects pages from `--repair-pages` and/or validation warnings;
4. fetches each page fresh by default;
5. parses and validates posts;
6. downloads or reuses images;
7. replaces posts for the selected pages only;
8. regenerates `thread.json`, `thread.md`, and `thread.html`;
9. updates page markers and resume state;
10. writes `repair_summary.json`.

If a repaired page validates cleanly, it is removed from `validation_warning_pages`. If not, it remains listed.

---

## Top 10 User Report

The `--top10` mode reads `thread.json`, counts posts by author, and writes `top10_report.json`.

Using `--thread-dir`:

```bash
python src/forexfactory_crawler.py --thread-dir "C:\PATH\TO\ARCHIVE_FOLDER" --top10
```

Using URL resolution:

```bash
python src/forexfactory_crawler.py --url "THREAD_URL" --output-root thread_archive --top10
```

The report includes:

- total posts;
- distinct users;
- rank;
- author;
- post count;
- share percentage.

---

## Offline HTML Exports

Offline exports read an existing `thread.json`. They do not scrape Forex Factory.

You can identify the archive with either:

```bash
--thread-dir "C:\PATH\TO\ARCHIVE_FOLDER"
```

or:

```bash
--url "THREAD_URL" --output-root thread_archive
```

### Single HTML Export

```bash
python src/forexfactory_crawler.py --thread-dir "C:\PATH\TO\ARCHIVE_FOLDER" --export-single-html
```

This creates a dark-mode HTML file with inline CSS and local image references.

Custom filename:

```bash
python src/forexfactory_crawler.py --thread-dir "C:\PATH\TO\ARCHIVE_FOLDER" --export-single-html --single-html-output local_full.html
```

### AI HTML Export

```bash
python src/forexfactory_crawler.py --thread-dir "C:\PATH\TO\ARCHIVE_FOLDER" --export-ai-html
```

This creates a dark-mode HTML file with inline CSS and embeds local images as base64 data URIs where possible.

Custom filename:

```bash
python src/forexfactory_crawler.py --thread-dir "C:\PATH\TO\ARCHIVE_FOLDER" --export-ai-html --ai-html-output ai_full.html
```

---

## Export Filters

Filters apply to `--export-single-html` and `--export-ai-html`.

They are applied in this order:

1. users;
2. pages;
3. post numbers.

### Filter by one user

```bash
python src/forexfactory_crawler.py --thread-dir "C:\PATH\TO\ARCHIVE_FOLDER" --export-single-html --users cpfleger
```

### Filter by multiple users

```bash
python src/forexfactory_crawler.py --thread-dir "C:\PATH\TO\ARCHIVE_FOLDER" --export-ai-html --users cpfleger,gringo2019,niks
```

### Filter by pages

```bash
python src/forexfactory_crawler.py --thread-dir "C:\PATH\TO\ARCHIVE_FOLDER" --export-single-html --pages 145,200-202
```

### Filter by post numbers

```bash
python src/forexfactory_crawler.py --thread-dir "C:\PATH\TO\ARCHIVE_FOLDER" --export-ai-html --posts 2886,3000-3050
```

A leading `#` is allowed:

```bash
python src/forexfactory_crawler.py --thread-dir "C:\PATH\TO\ARCHIVE_FOLDER" --export-ai-html --posts "#2886,#3000-#3050"
```

### Use a post list file

```bash
python src/forexfactory_crawler.py --thread-dir "C:\PATH\TO\ARCHIVE_FOLDER" --export-ai-html --posts-file selected_posts.txt
```

Example file contents:

```text
2886
3000-3050
4100, 4102, 4105-4110
```

### Combine filters

```bash
python src/forexfactory_crawler.py --thread-dir "C:\PATH\TO\ARCHIVE_FOLDER" --export-ai-html --users cpfleger --pages 145,200-202 --posts 2886,3000-3050
```

Combined filters mean posts must satisfy all selected filters.

---

## `thread.json` Data Model

Top-level structure:

```json
{
  "title": "Forex Factory Thread",
  "source_url": "https://www.forexfactory.com/thread/...",
  "start_page": 1,
  "archived_at": "2026-05-22T...Z",
  "total_posts": 123,
  "posts": []
}
```

Common post fields:

| Field | Description |
|---|---|
| `post_id` | Numeric Forex Factory post ID. |
| `post_number` | Visible thread post number without `#` or commas. |
| `post_url` | Absolute permalink. |
| `page` | Page number where the post was captured. |
| `author` | Extracted author or `Unknown`. |
| `timestamp` | Extracted timestamp or `Unknown date`. |
| `text` | Composed body, attachment, and signature text. |
| `body_text` | Main body only. |
| `signature_text` | Extracted signature text. |
| `attachment_labels` | Attachment labels, filenames, sizes, or download counts where detected. |
| `image_urls` | Original remote image URLs. |
| `images` | Local image paths. |
| `accepted` | Whether the post passed validation. |
| `validation_reasons` | Weaknesses or warnings found during validation. |

---

## Resume State

`resume_state.json` stores:

- base URL;
- title;
- requested start page;
- actual start page;
- last completed page;
- next page;
- detected last page;
- finished flag;
- average seconds per page;
- final page verification status;
- validation warning pages;
- unknown-date post totals;
- latest summary path;
- update timestamp.

To continue a previous scrape:

```bash
python src/forexfactory_crawler.py --url "THREAD_URL"
```

To ignore resume and restart exactly from a page:

```bash
python src/forexfactory_crawler.py --url "THREAD_URL" --start-page 50 --no-resume
```

To fetch fresh HTML and avoid normal resume inference:

```bash
python src/forexfactory_crawler.py --url "THREAD_URL" --start-page 50 --force
```

---

## Recommended Workflow

### 1. Smoke test

```bash
python src/forexfactory_crawler.py --url "THREAD_URL" --start-page 1 --max-pages 1 --debug
```

### 2. Full scrape

```bash
python src/forexfactory_crawler.py --url "THREAD_URL"
```

### 3. Continue later

```bash
python src/forexfactory_crawler.py --url "THREAD_URL"
```

### 4. Repair validation warnings

```bash
python src/forexfactory_crawler.py --url "THREAD_URL" --repair-validation-warnings
```

### 5. Report top posters

```bash
python src/forexfactory_crawler.py --url "THREAD_URL" --top10
```

### 6. Build a portable AI export

```bash
python src/forexfactory_crawler.py --url "THREAD_URL" --export-ai-html --ai-html-output full_ai.html
```

---

## Troubleshooting

### `Could not find existing archive file: thread.json`

The selected archive folder does not contain `thread.json`. Use the exact archive folder:

```bash
python src/forexfactory_crawler.py --thread-dir "C:\PATH\TO\ARCHIVE_FOLDER" --top10
```

or pass the same `--url` and `--output-root` used for scraping.

### Missing images in single HTML export

`--export-single-html` references local image paths. Keep the generated HTML file in the archive folder with the `images/` directory intact.

For a more portable file, use:

```bash
python src/forexfactory_crawler.py --thread-dir "C:\PATH\TO\ARCHIVE_FOLDER" --export-ai-html
```

### Missing posts, validation warnings, or unknown dates

Check:

- `last_run_summary.json`
- `resume_state.json`
- `page_state/page_XXXX.done.json`
- `scrape.log`

Then run:

```bash
python src/forexfactory_crawler.py --url "THREAD_URL" --repair-validation-warnings
```

or:

```bash
python src/forexfactory_crawler.py --url "THREAD_URL" --repair-pages 145,200-202
```

### Unexpected resume page

Resume uses several state sources. To force an exact page:

```bash
python src/forexfactory_crawler.py --url "THREAD_URL" --start-page 123 --no-resume
```

### Login does not work

Login depends on automatic form discovery. If Forex Factory changes its login flow or uses additional anti-bot checks, the script may continue as a public guest. Check `scrape.log` for login messages.

---

## Maintenance Notes

The parser is tuned for Forex Factory markup with selectors, regular expressions, and scoring heuristics.

If Forex Factory changes its HTML, inspect and update these areas first:

- `THREAD_TITLE_SELECTORS`
- `AUTHOR_SELECTORS`
- `DATE_SELECTORS`
- `CONTENT_SELECTORS`
- `POST_HREF_RE`
- `POST_LABEL_RE`
- `score_post_container()`
- `find_page_one_opener_block()`
- `extract_author()`
- `extract_timestamp_line()`
- `extract_post_sections()`

After parser changes, test with:

```bash
python src/forexfactory_crawler.py --url "THREAD_URL" --start-page 1 --max-pages 1 --debug --force
```

Then inspect:

- accepted post count;
- missing post numbers;
- unknown-date warnings;
- per-post JSON snapshots;
- `thread.md` readability;
- image download results.
