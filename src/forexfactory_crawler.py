import argparse
import base64
import mimetypes
import os
import copy
import getpass
import html
import json
import logging
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from tqdm import tqdm

# version 0.3.9

# --url                  Full thread URL
# --thread-dir           Direct path to an existing archived thread folder for offline modes
# --start-page           Start page number
# --username             Username/email if login is needed
# --password             Password if login is needed
# --output-root          Base output folder
# --max-pages            Optional safety limit for testing
# --force                Re-fetch cached raw HTML pages
# --debug                Show detailed console logging
# --no-resume            Ignore saved progress and start exactly from --start-page
# --overlap-start-pages  Optional 1-page overlap safety for live threads / deep starts
# --repair-pages         Reprocess specific page(s) inside an existing archive (e.g. 145 or 145,200-202)
# --repair-validation-warnings  Reprocess page(s) listed in the archive's validation warnings
# --top10                Report top 10 users by post count from an existing archive
# --export-single-html   Export a dark-mode single HTML file from an existing archive
# --users                Filter single HTML export by one or more comma-separated usernames
# --single-html-output   Custom filename for the offline single HTML export
# --export-ai-html       Export a dark-mode AI HTML file from an existing archive
# --ai-html-output       Custom filename for the offline AI HTML export
# --pages                Filter offline exports by specific archive page(s), e.g. 145 or 145,200-202
# --posts                Filter offline exports by thread post number(s), e.g. 2886 or 2886,3000-3050
# --posts-file           Read thread post numbers / ranges from a text file for offline exports





# ====================== QUICK USER MANUAL / CHEAT SHEET ======================
#
# LIVE SCRAPE
# ---------------------------------------------------------------------------
# Full thread scrape:
# python ffactory.py --url "https://www.forexfactory.com/thread/1190104-m1-countertrend-scalping-strategy"
#
# Start from a specific page:
# python ffactory.py --url "THREAD_URL" --start-page 101
#
# Limit pages for testing:
# python ffactory.py --url "THREAD_URL" --start-page 1 --max-pages 5
#
# Force re-fetch of cached raw HTML:
# python ffactory.py --url "THREAD_URL" --force
#
# Debug logging to console:
# python ffactory.py --url "THREAD_URL" --debug
#
# Disable resume and start exactly from --start-page:
# python ffactory.py --url "THREAD_URL" --start-page 1 --no-resume
#
# Use overlap pages for deep live restarts:
# python ffactory.py --url "THREAD_URL" --start-page 300 --overlap-start-pages 1
#
# Supply login credentials on command line:
# python ffactory.py --url "THREAD_URL" --username "YOUR_USER" --password "YOUR_PASS"
#
#
# REPAIR MODE
# ---------------------------------------------------------------------------
# Repair one page:
# python ffactory.py --url "THREAD_URL" --output-root thread_archive_full_run --repair-pages 145
#
# Repair multiple pages:
# python ffactory.py --url "THREAD_URL" --output-root thread_archive_full_run --repair-pages 145,200-202
#
# Repair pages previously flagged by validation warnings:
# python ffactory.py --url "THREAD_URL" --output-root thread_archive_full_run --repair-validation-warnings
#
#
# OFFLINE ARCHIVE MODES
# ---------------------------------------------------------------------------
# Use --thread-dir to work directly from an existing archive folder.
#
# Example archive folder:
# C:\Users\morgb\scripts\Crawler\thread_archive_full_run\1190104-m1-countertrend-scalping-strategy
#
# Top 10 posters from an existing archive:
# python ffactory.py --thread-dir "C:\PATH\TO\ARCHIVE_FOLDER" --top10
#
# Export local browsing HTML from an existing archive:
# python ffactory.py --thread-dir "C:\PATH\TO\ARCHIVE_FOLDER" --export-single-html
#
# Export portable AI HTML from an existing archive:
# python ffactory.py --thread-dir "C:\PATH\TO\ARCHIVE_FOLDER" --export-ai-html
#
#
# HTML EXPORT FILTERS
# ---------------------------------------------------------------------------
# Filter by one user:
# python ffactory.py --thread-dir "C:\PATH\TO\ARCHIVE_FOLDER" --export-single-html --users cpfleger
#
# Filter by multiple users:
# python ffactory.py --thread-dir "C:\PATH\TO\ARCHIVE_FOLDER" --export-ai-html --users cpfleger,gringo2019,niks
#
# Filter by pages:
# python ffactory.py --thread-dir "C:\PATH\TO\ARCHIVE_FOLDER" --export-single-html --pages 145,200-202
#
# Filter by specific post numbers:
# python ffactory.py --thread-dir "C:\PATH\TO\ARCHIVE_FOLDER" --export-ai-html --posts 2886,3000-3050
#
# Filter by post list file:
# python ffactory.py --thread-dir "C:\PATH\TO\ARCHIVE_FOLDER" --export-ai-html --posts-file selected_posts.txt
#
# Combine users + pages + posts:
# python ffactory.py --thread-dir "C:\PATH\TO\ARCHIVE_FOLDER" --export-ai-html --users cpfleger --pages 145,200-202 --posts 2886,3000-3050
#
#
# CUSTOM OUTPUT FILENAMES
# ---------------------------------------------------------------------------
# Local HTML with custom filename:
# python ffactory.py --thread-dir "C:\PATH\TO\ARCHIVE_FOLDER" --export-single-html --single-html-output local_full.html
#
# AI HTML with custom filename:
# python ffactory.py --thread-dir "C:\PATH\TO\ARCHIVE_FOLDER" --export-ai-html --ai-html-output ai_full.html
#
#
# FLAG REFERENCE
# ---------------------------------------------------------------------------
# --url
#   Full live thread URL. Used for scraping and currently also used for repair mode.
#
# --thread-dir
#   Direct path to an existing archived thread folder for offline report/export modes.
#
# --start-page
#   Page number to begin scraping from.
#
# --username / --password
#   Optional login credentials for sites/pages that need authentication.
#
# --output-root
#   Base output folder that contains archive folders.
#
# --max-pages
#   Safety limit for test runs.
#
# --force
#   Re-fetch cached raw HTML instead of reusing saved copies.
#
# --debug
#   Show detailed logging in the console as the script runs.
#
# --no-resume
#   Ignore resume state and start exactly from --start-page.
#
# --overlap-start-pages
#   Revisit a small page overlap when restarting deep into a live thread.
#
# --repair-pages
#   Reprocess specific archive page numbers.
#
# --repair-validation-warnings
#   Reprocess pages that were previously flagged by validation warnings.
#
# --top10
#   Report top 10 users by post count from an existing archive.
#
# --export-single-html
#   Build a dark-mode HTML export from an existing archive.
#
# --users
#   Comma-separated usernames for offline export filtering.
#
# --single-html-output
#   Custom output filename for --export-single-html.
#
# --export-ai-html
#   Build a dark-mode AI HTML export from an existing archive.
#
# --ai-html-output
#   Custom output filename for --export-ai-html.
#
# --pages
#   Comma-separated archive page filter, e.g. 145 or 145,200-202.
#
# --posts
#   Comma-separated thread post-number filter, e.g. 2886 or 2886,3000-3050.
#
# --posts-file
#   Text file containing post numbers and/or ranges for offline export filtering.
#
#
# IMPORTANT NOTES
# ---------------------------------------------------------------------------
# 1. --export-single-html and --export-ai-html are ACTION flags.
#    --single-html-output and --ai-html-output only set the filename.
#
# 2. If you use --single-html-output, you must also include --export-single-html.
#
# 3. If you use --ai-html-output, you must also include --export-ai-html.
#
# 4. --thread-dir is for offline archive work.
#    Live scraping still uses --url.
#
# 5. Good first test:
#    python ffactory.py --url "THREAD_URL" --start-page 1 --max-pages 1 --debug
#
# ============================================================================
#
#
#
#
#
#
# ====================== AI HTML EXPORT CHEAT SHEET ======================
#
# NOTE:
# --export-ai-html = portable single-file export
# --ai-html-output = optional custom filename
#
# Base archive used in these examples:
# C:\Users\morgb\scripts\Crawler\thread_archive_full_1390260\1390260-less-trades-more-precision-a-clean-price
#
#
# FULL AI EXPORT
# ----------------------------------------------------------------------
# python ffactory.py --thread-dir "C:\Users\morgb\scripts\Crawler\thread_archive_full_1390260\1390260-less-trades-more-precision-a-clean-price" --export-ai-html
#
#
# FULL AI EXPORT + CUSTOM FILENAME
# ----------------------------------------------------------------------
# python ffactory.py --thread-dir "C:\Users\morgb\scripts\Crawler\thread_archive_full_1390260\1390260-less-trades-more-precision-a-clean-price" --export-ai-html --ai-html-output full_ai.html
#
#
# SINGLE USER AI EXPORT
# ----------------------------------------------------------------------
# python ffactory.py --thread-dir "C:\Users\morgb\scripts\Crawler\thread_archive_full_1390260\1390260-less-trades-more-precision-a-clean-price" --export-ai-html --users cpfleger
#
#
# MULTIPLE USERS AI EXPORT
# ----------------------------------------------------------------------
# python ffactory.py --thread-dir "C:\Users\morgb\scripts\Crawler\thread_archive_full_1390260\1390260-less-trades-more-precision-a-clean-price" --export-ai-html --users cpfleger,gringo2019,niks
#
#
# CUSTOM PAGES AI EXPORT
# ----------------------------------------------------------------------
# python ffactory.py --thread-dir "C:\Users\morgb\scripts\Crawler\thread_archive_full_1390260\1390260-less-trades-more-precision-a-clean-price" --export-ai-html --pages 1,3,5-7
#
#
# CUSTOM POSTS AI EXPORT
# ----------------------------------------------------------------------
# python ffactory.py --thread-dir "C:\Users\morgb\scripts\Crawler\thread_archive_full_1390260\1390260-less-trades-more-precision-a-clean-price" --export-ai-html --posts 100,145,200,3000-3050
#
#
# POSTS FROM A TEXT FILE
# ----------------------------------------------------------------------
# python ffactory.py --thread-dir "C:\Users\morgb\scripts\Crawler\thread_archive_full_1390260\1390260-less-trades-more-precision-a-clean-price" --export-ai-html --posts-file selected_posts.txt
#
#
# USERS + PAGES
# ----------------------------------------------------------------------
# python ffactory.py --thread-dir "C:\Users\morgb\scripts\Crawler\thread_archive_full_1390260\1390260-less-trades-more-precision-a-clean-price" --export-ai-html --users cpfleger,gringo2019 --pages 2-4
#
#
# USERS + POSTS
# ----------------------------------------------------------------------
# python ffactory.py --thread-dir "C:\Users\morgb\scripts\Crawler\thread_archive_full_1390260\1390260-less-trades-more-precision-a-clean-price" --export-ai-html --users cpfleger --posts 2886,3000-3050
#
#
# PAGES + CUSTOM FILENAME
# ----------------------------------------------------------------------
# python ffactory.py --thread-dir "C:\Users\morgb\scripts\Crawler\thread_archive_full_1390260\1390260-less-trades-more-precision-a-clean-price" --export-ai-html --pages 1-3 --ai-html-output pages_1_3_ai.html
#
#
# POSTS + CUSTOM FILENAME
# ----------------------------------------------------------------------
# python ffactory.py --thread-dir "C:\Users\morgb\scripts\Crawler\thread_archive_full_1390260\1390260-less-trades-more-precision-a-clean-price" --export-ai-html --posts 100,145,200 --ai-html-output selected_posts_ai.html
#
# ======================================================================


# ====================== FOREX FACTORY – THREAD TUNING ======================
THREAD_TITLE_SELECTORS = ["h1"]
AUTHOR_SELECTORS = [".author", ".username", "[class*='author']", "[class*='user']"]
DATE_SELECTORS = [".date", "time", "[class*='date']", "[class*='time']"]
CONTENT_SELECTORS = [
    ".message",
    ".content",
    ".post-content",
    ".postbody",
    "[class*='message']",
    "[class*='content']",
]

LOGIN_PAGE_URL = "https://www.forexfactory.com/"
REQUEST_DELAY_SECONDS = 1.8
IMAGE_DELAY_SECONDS = 0.25
REQUEST_TIMEOUT = 20
MAX_RETRIES = 5
DEFAULT_OUTPUT_ROOT = Path("thread_archive")

RESUME_STATE_FILENAME = "resume_state.json"
PAGE_MARKERS_DIRNAME = "page_state"
LAST_RUN_SUMMARY_FILENAME = "last_run_summary.json"
TOP10_REPORT_FILENAME = "top10_report.json"
SINGLE_HTML_EXPORT_REPORT_FILENAME = "single_html_export_report.json"
AI_HTML_EXPORT_REPORT_FILENAME = "ai_html_export_report.json"
PARTIAL_FILE_SUFFIX = ".part"

INITIAL_ESTIMATED_SECONDS_PER_PAGE = 15.0
ETA_WARMUP_PAGES = 2
ROLLING_AVG_WINDOW = 5

PAGE_VALIDATION_RETRY_LIMIT = 1
DEFAULT_OVERLAP_START_PAGES = 0
PROGRESS_MIN_INTERVAL_SECONDS = 0.25

EXPORT_IMAGE_DISPLAY_WIDTH_PX = 1400
EXPORT_CONTENT_MAX_WIDTH_PX = 1600
POST_IMAGE_PLACEHOLDER = "[[POST_IMAGE]]"
# ==========================================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/134.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}

MONTH_RE = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
ABSOLUTE_TIMESTAMP_RE = re.compile(
    rf"{MONTH_RE}\s+\d{{1,2}},\s+(?:\d{{4}}\s+)?\d{{1,2}}:\d{{2}}(?:am|pm)(?:\s*\([^)]*\))?",
    re.I,
)
EDITED_TIMESTAMP_RE = re.compile(
    rf"Edited\s+{MONTH_RE}\s+\d{{1,2}},\s+(?:\d{{4}}\s+)?\d{{1,2}}:\d{{2}}(?:am|pm)",
    re.I,
)
DATE_LINE_RE = re.compile(
    rf"(?:Edited\s+)?{MONTH_RE}\s+\d{{1,2}},\s+(?:\d{{4}}\s+)?\d{{1,2}}:\d{{2}}(?:am|pm)(?:\s*\([^)]*\))?"
    rf"(?:\s*\|\s*Edited\s+{MONTH_RE}\s+\d{{1,2}},\s+(?:\d{{4}}\s+)?\d{{1,2}}:\d{{2}}(?:am|pm))?",
    re.I,
)
POST_HREF_RE = re.compile(r"/thread/post/(\d+)")
POST_LABEL_RE = re.compile(r"#\s*([\d,]+)")
IMAGE_EXT_RE = re.compile(r"\.(?:jpg|jpeg|png|gif|webp|bmp|svg)(?:\?|$)", re.I)

SKIP_IMAGE_HINTS = ("avatar", "smiley", "emoji", "icon", "logo", "sprite", "blank", "spacer", "pixel")
BAD_AUTHOR_TEXTS = {
    "quote",
    "reply",
    "subscribe",
    "forums",
    "trades",
    "news",
    "calendar",
    "market",
    "brokers",
    "create account",
    "login",
    "logout",
    "search",
    "top of page",
    "more",
}

COMMON_MOJIBAKE_REPLACEMENTS = {
    "â€™": "’",
    "â€˜": "‘",
    "â€œ": "“",
    "â€": "”",
    "â€“": "–",
    "â€”": "—",
    "â€¦": "…",
    "Â ": " ",
    "Â ": " ",
    "﻿": "",
}

ATTACHMENT_TEXT_BLACKLIST = {
    "",
    "image",
    "attached image",
    "click to enlarge",
    "download",
}
ATTACHMENT_FILE_HEADING_RE = re.compile(r"^Attached File\(s\)$", re.I)
ATTACHMENT_SIZE_RE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:KB|MB|GB|bytes?)\b", re.I)
ATTACHMENT_DOWNLOADS_RE = re.compile(r"\b\d+[\d,]*\s+downloads\b", re.I)
ATTACHMENT_ICON_HINTS = ("/images/attach/", "file type:")


def get_bs_parser() -> str:
    try:
        BeautifulSoup("<html></html>", "lxml")
        return "lxml"
    except Exception:
        return "html.parser"


BS_PARSER = get_bs_parser()


def repair_cp1252_controls(text: str) -> str:
    if not text:
        return ""
    repaired = []
    for ch in text:
        code = ord(ch)
        if 0x80 <= code <= 0x9F:
            try:
                repaired.append(bytes([code]).decode("cp1252"))
            except Exception:
                repaired.append(ch)
        else:
            repaired.append(ch)
    return "".join(repaired)


def repair_mojibake(text: str) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = repair_cp1252_controls(text)
    for bad, good in COMMON_MOJIBAKE_REPLACEMENTS.items():
        text = text.replace(bad, good)
    return text


def normalize_space(text: str) -> str:
    repaired = repair_mojibake(text or "")
    return re.sub(r"\s+", " ", repaired).strip()


def slugify(text: str, max_len: int = 80) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", (text or "").strip().lower()).strip("-")
    return text[:max_len] or "thread"


def safe_filename(text: str, max_len: int = 120) -> str:
    text = re.sub(r"[^\w.\-]+", "_", text or "").strip("._")
    return (text[:max_len] or "file").strip("._") or "file"


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def clear_console() -> None:
    try:
        os.system("cls" if os.name == "nt" else "clear")
    except Exception:
        pass


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    temp_path = path.with_name(path.name + PARTIAL_FILE_SUFFIX)
    temp_path.write_bytes(payload)
    temp_path.replace(path)


def atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    atomic_write_bytes(path, content.encode(encoding))


def atomic_write_json(path: Path, payload: dict) -> None:
    atomic_write_text(path, json.dumps(payload, indent=2, ensure_ascii=False))


def cleanup_partial_files(root_dir: Path, logger: logging.Logger) -> int:
    removed = 0
    if not root_dir.exists():
        return removed

    for part_path in root_dir.rglob(f"*{PARTIAL_FILE_SUFFIX}"):
        try:
            part_path.unlink()
            removed += 1
        except Exception as exc:
            logger.warning("Could not remove partial file %s: %s", part_path, exc)

    if removed:
        logger.info("Removed %s leftover partial file(s) from a previous interrupted run.", removed)
    return removed


def setup_logger(log_path: Path, debug: bool = False) -> logging.Logger:
    logger = logging.getLogger("forexfactory_archiver")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if debug:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    return logger


def load_json_file(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def normalize_thread_url(url: str) -> str:
    parsed = urlparse(url.strip())
    query = parse_qs(parsed.query, keep_blank_values=True)
    query.pop("page", None)
    new_query = urlencode(query, doseq=True)
    cleaned = parsed._replace(query=new_query, fragment="")
    return urlunparse(cleaned).rstrip("?")


def get_page_url(base_url: str, page_num: int) -> str:
    parsed = urlparse(normalize_thread_url(base_url))
    query = parse_qs(parsed.query, keep_blank_values=True)
    if page_num > 1:
        query["page"] = [str(page_num)]
    else:
        query.pop("page", None)
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def request_with_retries(
    session: requests.Session,
    url: str,
    logger: logging.Logger,
    stream: bool = False,
) -> requests.Response:
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT, stream=stream)
            response.raise_for_status()
            return response
        except Exception as exc:
            last_error = exc
            wait_time = min(2 ** attempt, 8)
            logger.warning("Request failed (%s/%s) for %s: %s", attempt, MAX_RETRIES, url, exc)
            if attempt < MAX_RETRIES:
                time.sleep(wait_time)
    raise RuntimeError(f"Failed after {MAX_RETRIES} attempts: {url}") from last_error


def fetch_html(
    session: requests.Session,
    page_url: str,
    raw_html_path: Path,
    logger: logging.Logger,
    force: bool = False,
) -> tuple[str, bool]:
    if raw_html_path.exists() and not force:
        logger.info("Using cached HTML: %s", raw_html_path.name)
        return raw_html_path.read_text(encoding="utf-8", errors="replace"), True

    response = request_with_retries(session, page_url, logger=logger, stream=False)
    html = response.text
    atomic_write_text(raw_html_path, html, encoding="utf-8")
    return html, False


def discover_login_form(soup: BeautifulSoup, current_url: str):
    for form in soup.find_all("form"):
        form_html = str(form).lower()
        has_password = (
            form.find("input", attrs={"type": re.compile("password", re.I)}) is not None
            or "password" in form_html
        )
        if has_password:
            action = form.get("action") or current_url
            return form, urljoin(current_url, action)
    return None, None


def build_login_payload(form: Tag, username: str, password: str) -> dict:
    payload = {}
    for input_tag in form.find_all("input"):
        name = input_tag.get("name")
        if not name:
            continue
        payload[name] = input_tag.get("value", "")

    user_field = None
    pass_field = None
    for name in list(payload.keys()):
        low = name.lower()
        if user_field is None and any(token in low for token in ("user", "email", "login")):
            user_field = name
        if pass_field is None and "pass" in low:
            pass_field = name

    if user_field is None:
        user_field = "username"
        payload[user_field] = ""
    if pass_field is None:
        pass_field = "password"
        payload[pass_field] = ""

    payload[user_field] = username
    payload[pass_field] = password
    return payload


def login_if_requested(session: requests.Session, username: str, password: str, logger: logging.Logger) -> bool:
    if not username or not password:
        logger.info("No login credentials supplied; scraping as a public guest.")
        return False

    logger.info("Credentials supplied; attempting form discovery login.")
    response = request_with_retries(session, LOGIN_PAGE_URL, logger=logger, stream=False)
    soup = BeautifulSoup(response.text, BS_PARSER)
    form, action_url = discover_login_form(soup, response.url)

    if form is None or action_url is None:
        logger.warning("Could not discover a login form automatically. Continuing without forcing login.")
        return False

    payload = build_login_payload(form, username=username, password=password)
    post_response = session.post(action_url, data=payload, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    if post_response.status_code >= 400:
        logger.warning("Login POST returned %s. Continuing, but authenticated scraping may not be active.", post_response.status_code)
        return False

    verify_response = request_with_retries(session, LOGIN_PAGE_URL, logger=logger, stream=False)
    verify_text = verify_response.text.lower()
    logged_in = "logout" in verify_text or "log out" in verify_text

    if logged_in:
        logger.info("Login appears to have succeeded.")
    else:
        logger.warning("Could not verify login success. Public scraping will still proceed.")
    return logged_in


def first_text_match(node: Tag, selectors: list[str]) -> str:
    for selector in selectors:
        match = node.select_one(selector)
        if match:
            text = normalize_space(match.get_text(" ", strip=True))
            if text:
                return text
    return ""


def parse_thread_title(soup: BeautifulSoup) -> str:
    for selector in THREAD_TITLE_SELECTORS:
        match = soup.select_one(selector)
        if match:
            title = normalize_space(match.get_text(" ", strip=True))
            if title:
                return title
    title_tag = soup.find("title")
    if title_tag:
        return normalize_space(title_tag.get_text(" ", strip=True))
    return "Forex Factory Thread"


def parse_last_page(
    soup: BeautifulSoup,
    current_page: int,
    current_page_url: str,
) -> int | None:
    max_page = current_page
    found_any = False

    normalized_current = normalize_thread_url(current_page_url or "")
    parsed_current = urlparse(normalized_current)
    current_host = parsed_current.netloc.lower()
    current_path = parsed_current.path.rstrip("/")

    for a in soup.find_all("a", href=True):
        href = (a.get("href") or "").strip()
        if not href:
            continue

        full = urljoin(current_page_url or LOGIN_PAGE_URL, href)
        normalized_full = normalize_thread_url(full)
        parsed_full = urlparse(normalized_full)

        if current_host and parsed_full.netloc.lower() != current_host:
            continue
        if current_path and parsed_full.path.rstrip("/") != current_path:
            continue

        raw_query = parse_qs(urlparse(full).query)
        page_values = raw_query.get("page", [])
        if page_values and page_values[0].isdigit():
            max_page = max(max_page, int(page_values[0]))
            found_any = True
            continue

        text = normalize_space(a.get_text(" ", strip=True))
        if text.isdigit():
            max_page = max(max_page, int(text))
            found_any = True

    return max_page if found_any else None


def is_post_permalink_anchor(a: Tag) -> bool:
    href = a.get("href", "")
    return bool(POST_HREF_RE.search(href))


def is_post_number_anchor(a: Tag) -> bool:
    if not is_post_permalink_anchor(a):
        return False
    text = normalize_space(a.get_text(" ", strip=True))
    return bool(POST_LABEL_RE.fullmatch(text))


def dedupe_tags(nodes: list[Tag]) -> list[Tag]:
    seen = set()
    result = []
    for node in nodes:
        key = id(node)
        if key not in seen:
            seen.add(key)
            result.append(node)
    return result


def normalize_attachment_image_url(url: str) -> str:
    if "/attachment/image/" in url and "/thumbnail" in url:
        url = url.replace("/thumbnail", "")
    return url


def should_skip_image(url: str) -> bool:
    low = url.lower()
    return any(hint in low for hint in SKIP_IMAGE_HINTS)


def normalize_timestamp_candidate(text: str) -> str:
    matches = ABSOLUTE_TIMESTAMP_RE.findall(text)
    if matches:
        unique = []
        for item in matches:
            norm = normalize_space(item)
            if not unique or unique[-1] != norm:
                unique.append(norm)
        return " | ".join(unique)
    edited = EDITED_TIMESTAMP_RE.findall(text)
    if edited:
        unique = []
        for item in edited:
            norm = normalize_space(item)
            if not unique or unique[-1] != norm:
                unique.append(norm)
        return " | ".join(unique)
    return ""


def extract_expected_post_numbers(soup: BeautifulSoup) -> list[str]:
    labels = []
    seen = set()
    for a in soup.find_all("a", href=True):
        if not is_post_number_anchor(a):
            continue
        text = normalize_space(a.get_text(" ", strip=True))
        match = POST_LABEL_RE.search(text)
        if not match:
            continue
        label = match.group(1).replace(",", "")
        if label not in seen:
            seen.add(label)
            labels.append(label)
    return labels


def score_post_container(parent: Tag, anchor: Tag) -> float:
    classes = " ".join(parent.get("class", []))
    low_classes = classes.lower()
    if "quote" in low_classes or "blockquote" in low_classes:
        return float("-inf")
    if parent.name in {"blockquote"}:
        return float("-inf")

    text = normalize_space(parent.get_text(" ", strip=True))
    if len(text) < 30:
        return float("-inf")

    number_anchor_count = 0
    permalink_count = 0
    for a in parent.find_all("a", href=True):
        if is_post_permalink_anchor(a):
            permalink_count += 1
        if is_post_number_anchor(a):
            number_anchor_count += 1

    if number_anchor_count != 1:
        return float("-inf")
    if permalink_count > 6:
        return float("-inf")

    score = 0.0
    score += min(len(text) / 120.0, 4.0)

    if first_text_match(parent, DATE_SELECTORS):
        score += 4.0
    elif normalize_timestamp_candidate(text):
        score += 3.0

    if "joined" in text.lower():
        score += 1.0
    if "quote" in text:
        score += 0.5
    if "attached image" in text.lower():
        score += 0.5

    content_node = choose_content_node(parent)
    content_len = len(normalize_space(content_node.get_text(" ", strip=True)))
    if content_len >= 20:
        score += min(content_len / 200.0, 4.0)

    if parent.name in {"div", "article", "li", "section"}:
        score += 0.5

    if parent is anchor:
        score -= 4.0

    return score


def choose_post_container(anchor: Tag) -> Tag | None:
    best_parent = None
    best_score = float("-inf")

    for parent in [anchor] + [p for p in anchor.parents if isinstance(p, Tag)]:
        if parent.name in {"body", "html"}:
            break
        score = score_post_container(parent, anchor)
        if score > best_score:
            best_parent = parent
            best_score = score

        text = normalize_space(parent.get_text(" ", strip=True))
        if len(text) > 4000:
            break

    return best_parent if best_score > 1.0 else None


def sort_blocks_by_post_label(blocks: list[Tag]) -> list[Tag]:
    def key(block: Tag) -> tuple:
        _, label, _ = extract_post_id_and_label(block, page_url="")
        try:
            return (int(label or 0),)
        except Exception:
            return (0,)

    return sorted(blocks, key=key)


def score_page_one_opener_candidate(node: Tag, thread_title: str) -> float:
    classes = " ".join(node.get("class", []))
    low_classes = classes.lower()

    if node.name in {"script", "style", "noscript", "svg", "path"}:
        return float("-inf")
    if any(bad in low_classes for bad in ("quote", "breadcrumb", "pagination", "toolbar", "footer")):
        return float("-inf")

    text = normalize_space(node.get_text(" ", strip=True))
    if len(text) < 80 or len(text) > 12000:
        return float("-inf")

    if thread_title and normalize_space(text) == normalize_space(thread_title):
        return float("-inf")

    number_anchor_count = sum(1 for a in node.find_all("a", href=True) if is_post_number_anchor(a))
    if number_anchor_count:
        return float("-inf")

    permalink_count = sum(1 for a in node.find_all("a", href=True) if is_post_permalink_anchor(a))
    if permalink_count > 1:
        return float("-inf")

    score = 0.0
    score += min(len(text) / 180.0, 5.0)

    author = extract_author(node)
    if author and author != "Unknown":
        score += 2.0

    timestamp = extract_timestamp_line(node)
    if timestamp and timestamp != "Unknown date":
        score += 4.0
    elif normalize_timestamp_candidate(text):
        score += 3.0

    if "joined" in text.lower():
        score += 1.0

    content_node = choose_content_node(node)
    content_len = len(normalize_space(content_node.get_text(" ", strip=True)))
    if content_len >= 80:
        score += min(content_len / 250.0, 4.0)

    if node.name in {"div", "article", "section", "li", "td"}:
        score += 0.5

    return score


def find_page_one_opener_block(soup: BeautifulSoup, blocks: list[Tag]) -> Tag | None:
    if not blocks:
        return None

    sorted_blocks = sort_blocks_by_post_label(dedupe_tags(blocks))
    first_block = sorted_blocks[0]
    _, first_label, _ = extract_post_id_and_label(first_block, page_url="")
    if first_label not in {"2", ""}:
        return None

    thread_title = parse_thread_title(soup)
    best_node = None
    best_score = float("-inf")
    seen_ids = {id(block) for block in sorted_blocks}

    current: Tag | None = first_block
    depth = 0
    while isinstance(current, Tag) and current.name not in {"body", "html"} and depth < 6:
        previous_siblings = [sib for sib in current.previous_siblings if isinstance(sib, Tag)]
        for sibling in reversed(previous_siblings):
            candidates = [sibling]
            candidates.extend(desc for desc in sibling.find_all(True))
            for candidate in candidates:
                if id(candidate) in seen_ids:
                    continue
                if any(id(parent) in seen_ids for parent in candidate.parents if isinstance(parent, Tag)):
                    continue

                score = score_page_one_opener_candidate(candidate, thread_title=thread_title)
                if score > best_score:
                    best_node = candidate
                    best_score = score
        parent = current.parent
        current = parent if isinstance(parent, Tag) else None
        depth += 1

    if best_node is not None and best_score >= 5.0:
        best_node["data-ff-opener"] = "1"
        return best_node

    return None


def detect_post_blocks(soup: BeautifulSoup, page_num: int | None = None) -> list[Tag]:
    blocks_by_label: dict[str, Tag] = {}

    for a in soup.find_all("a", href=True):
        if not is_post_number_anchor(a):
            continue
        container = choose_post_container(a)
        if container is None:
            continue
        _, label, _ = extract_post_id_and_label(container, page_url="")
        if not label:
            continue
        existing = blocks_by_label.get(label)
        if existing is None or len(str(container)) > len(str(existing)):
            blocks_by_label[label] = container

    blocks = list(blocks_by_label.values())
    if blocks:
        blocks = sort_blocks_by_post_label(dedupe_tags(blocks))
        if page_num == 1:
            opener_block = find_page_one_opener_block(soup, blocks)
            if opener_block is not None:
                blocks = [opener_block] + blocks
        return blocks

    # Fallback only if the page structure changed and number anchors were not enough.
    candidates = []
    for a in soup.find_all("a", href=True):
        if not is_post_permalink_anchor(a):
            continue
        container = choose_post_container(a)
        if container is not None:
            candidates.append(container)
    blocks = dedupe_tags(candidates)
    if page_num == 1 and blocks:
        opener_block = find_page_one_opener_block(soup, blocks)
        if opener_block is not None and opener_block not in blocks:
            blocks = [opener_block] + blocks
    return blocks


def get_post_number_anchor(block: Tag) -> Tag | None:
    for a in block.find_all("a", href=True):
        if is_post_number_anchor(a):
            return a
    return None


def get_primary_post_anchor(block: Tag) -> Tag | None:
    number_anchor = get_post_number_anchor(block)
    if number_anchor is not None:
        return number_anchor
    for a in block.find_all("a", href=True):
        if is_post_permalink_anchor(a):
            return a
    return None


def extract_post_id_and_label(block: Tag, page_url: str) -> tuple[str, str, str]:
    anchor = get_primary_post_anchor(block)
    post_id = ""
    post_label = ""
    post_url = page_url

    if anchor is not None:
        href = urljoin(page_url or LOGIN_PAGE_URL, anchor.get("href", ""))
        post_url = href
        match = POST_HREF_RE.search(href)
        if match:
            post_id = match.group(1)
        text = normalize_space(anchor.get_text(" ", strip=True))
        label_match = POST_LABEL_RE.search(text)
        if label_match:
            post_label = label_match.group(1).replace(",", "")

    return post_id, post_label, post_url


def extract_author(block: Tag) -> str:
    author = first_text_match(block, AUTHOR_SELECTORS)
    if author:
        return author

    for a in block.find_all("a", href=True):
        text = normalize_space(a.get_text(" ", strip=True))
        href = a.get("href", "")
        low = text.lower()

        if not text or low in BAD_AUTHOR_TEXTS:
            continue
        if text.startswith("#") or low.startswith("quoting "):
            continue
        if "posts" in low or text.isdigit():
            continue
        if href.startswith("http") and "forexfactory.com" not in href:
            continue
        if "/thread/post/" in href or "/attachment/" in href:
            continue
        if len(text) > 40:
            continue
        return text

    for item in block.stripped_strings:
        line = normalize_space(item)
        low = line.lower()
        if not line or low in BAD_AUTHOR_TEXTS:
            continue
        if low.startswith("quoting "):
            continue
        if DATE_LINE_RE.search(line):
            continue
        if is_stats_line(line):
            continue
        if len(line) <= 30 and " " not in line:
            return line

    return "Unknown"


def extract_timestamp_line(block: Tag) -> str:
    for selector in DATE_SELECTORS:
        for node in block.select(selector):
            candidate = normalize_timestamp_candidate(node.get_text(" ", strip=True))
            if candidate:
                return candidate

    anchor = get_primary_post_anchor(block)
    if anchor is not None:
        parent = anchor.parent if isinstance(anchor.parent, Tag) else None
        if parent is not None:
            candidate = normalize_timestamp_candidate(parent.get_text(" ", strip=True))
            if candidate:
                return candidate

    strings = []
    for idx, item in enumerate(block.stripped_strings):
        strings.append(normalize_space(item))
        if idx >= 39:
            break

    joined = " | ".join(strings)
    candidate = normalize_timestamp_candidate(joined)
    if candidate:
        return candidate

    for line in strings:
        candidate = normalize_timestamp_candidate(line)
        if candidate:
            return candidate

    return "Unknown date"


def is_stats_line(line: str) -> bool:
    low = line.lower()
    return ("joined " in low and "posts" in low) or low.startswith("| joined ")


def is_noise_line(line: str, author: str, timestamp: str, post_label: str) -> bool:
    low = line.lower()
    if not line:
        return True
    # Do not blanket-remove lines that match the author name.
    # Some Forex Factory posts include the username as real post text,
    # often immediately before an attachment section.
    if timestamp != "Unknown date" and normalize_space(line) == normalize_space(timestamp):
        return True
    if post_label and normalize_space(line).startswith(f"# {post_label}"):
        return True
    if low in {"quote", "reply to thread", "subscribe", "more", "top of page", "image"}:
        return True
    if low in {"disliked", "ignored"}:
        return True
    if is_stats_line(line):
        return True
    if re.fullmatch(r"\d+", line):
        return True
    return False


def is_quote_like_tag(tag: Tag) -> bool:
    if not isinstance(tag, Tag):
        return False
    if tag.name == "blockquote":
        return True

    attrs = " ".join(tag.get("class", []))
    if tag.get("id"):
        attrs += " " + str(tag.get("id"))
    low = attrs.lower()

    if "quote" not in low:
        return False

    # Avoid treating entire post containers as quotes.
    if tag.find("a", href=True) and any(is_post_number_anchor(a) for a in tag.find_all("a", href=True)):
        return False

    return True


def top_level_quote_containers(node: Tag) -> list[Tag]:
    containers: list[Tag] = []
    for tag in node.find_all(True):
        if not is_quote_like_tag(tag):
            continue
        if any(existing is ancestor for ancestor in tag.parents if isinstance(ancestor, Tag) for existing in containers):
            continue
        containers.append(tag)
    return containers


def format_quote_container_text(
    quote_node: Tag,
    author: str,
    timestamp: str,
    post_label: str,
) -> str:
    quote_lines: list[str] = []
    header_added = False
    payload_added = False

    for raw in quote_node.stripped_strings:
        line = normalize_space(raw)
        if not line:
            continue

        low = line.lower()

        # Forex Factory quote widgets often contain "Disliked" before the quote
        # and "Ignored" immediately after it. Anything after "Ignored" belongs to
        # the normal reply body, not the quote block.
        if low == "disliked":
            continue
        if low == "ignored":
            break

        if is_noise_line(line, author=author, timestamp=timestamp, post_label=post_label):
            continue

        if "{quote}" in low:
            line = normalize_space(re.sub(r"\{quote\}", "", line, flags=re.I))
            low = line.lower()
        if not line:
            continue

        if low.startswith("attached image"):
            line = "{image}"

        if low.startswith("quoting "):
            if not header_added:
                prefixed = f"> {line}"
                quote_lines.append(prefixed)
                header_added = True
            continue

        # Forex Factory's visible quote widget is usually a compact preview:
        # one quote header line plus one payload line. If the surrounding HTML
        # wrapper is too broad, any later lines are usually the author's reply,
        # not part of the quoted preview. Stop after the first payload line.
        if payload_added:
            break

        prefixed = f"> {line}"
        if not quote_lines or quote_lines[-1] != prefixed:
            quote_lines.append(prefixed)
        payload_added = True

    return "\n".join(quote_lines).strip()



def extract_text_lines_preserving_layout(node: Tag) -> list[str]:
    working_node = copy.deepcopy(node)

    # Preserve visual line breaks and avoid splitting inline text around links/emojis.
    for br in list(working_node.find_all("br")):
        br.replace_with(NavigableString("\n"))

    for img in list(working_node.find_all("img")):
        alt = normalize_space(img.get("alt", ""))
        title = normalize_space(img.get("title", ""))
        low_blob = f"{alt} {title}".lower()
        replacement = " "
        if "emoji" in low_blob or "smiley" in low_blob:
            replacement = " "
        img.replace_with(NavigableString(replacement))

    block_double_break_tags = {"p", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6"}
    block_single_break_tags = {"div", "li", "tr", "table", "ul", "ol", "hr"}

    for tag in working_node.find_all(True):
        if tag.name in block_double_break_tags:
            tag.append(NavigableString("\n\n"))
        elif tag.name in block_single_break_tags:
            tag.append(NavigableString("\n"))

    text = working_node.get_text(separator="", strip=False)
    text = text.replace("\xa0", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    lines: list[str] = []
    blank_run = 0
    for raw_line in text.split("\n"):
        line = normalize_space(raw_line)
        if not line:
            blank_run += 1
            if blank_run <= 2:
                lines.append("")
            continue
        blank_run = 0
        lines.append(line)
    return lines

def build_text_from_node(node: Tag, author: str, timestamp: str, post_label: str) -> str:
    lines: list[str] = []
    quote_lines: list[str] = []
    in_quote = False
    previous_nonblank = ""

    def flush_quote_block() -> None:
        nonlocal quote_lines
        if not quote_lines:
            return
        deduped_quote: list[str] = []
        prev_q = None
        for qline in quote_lines:
            if qline != prev_q:
                deduped_quote.append(qline)
            prev_q = qline
        lines.extend(deduped_quote)
        quote_lines = []

    raw_lines = extract_text_lines_preserving_layout(node)

    for raw in raw_lines:
        line = raw.rstrip()

        if not line:
            if in_quote:
                flush_quote_block()
                in_quote = False
            if lines and lines[-1] != "":
                lines.append("")
            previous_nonblank = ""
            continue

        low = line.lower()

        if low.startswith("quoting "):
            flush_quote_block()
            if lines and lines[-1] != "":
                lines.append("")
            in_quote = True
            quote_lines = [f"> {line}"]
            previous_nonblank = line
            continue

        if low == "disliked":
            previous_nonblank = line
            continue

        if low == "ignored":
            flush_quote_block()
            if lines and lines[-1] != "":
                lines.append("")
            in_quote = False
            previous_nonblank = line
            continue

        if "{quote}" in low:
            line = normalize_space(re.sub(r"\{quote\}", "", line, flags=re.I))
            low = line.lower()
            if not line:
                previous_nonblank = ""
                continue

        if low.startswith("attached image"):
            placeholder = f"> {{image}}" if in_quote else POST_IMAGE_PLACEHOLDER
            target = quote_lines if in_quote else lines
            if not target or target[-1] != placeholder:
                target.append(placeholder)
            previous_nonblank = line
            continue

        if is_noise_line(line, author=author, timestamp=timestamp, post_label=post_label):
            previous_nonblank = line
            continue

        if in_quote:
            prefixed = f"> {line}"
            if not quote_lines or quote_lines[-1] != prefixed:
                quote_lines.append(prefixed)
            previous_nonblank = line
            continue

        lines.append(line)
        previous_nonblank = line

    flush_quote_block()

    cleaned_lines: list[str] = []
    previous = None
    for line in lines:
        if line == "" and (not cleaned_lines or cleaned_lines[-1] == ""):
            continue
        if line != previous or line == "":
            cleaned_lines.append(line)
        previous = line

    while cleaned_lines and cleaned_lines[0] == "":
        cleaned_lines.pop(0)
    while cleaned_lines and cleaned_lines[-1] == "":
        cleaned_lines.pop()

    return "\n".join(cleaned_lines).strip()


def choose_content_node(block: Tag) -> Tag:
    candidates = []
    for selector in CONTENT_SELECTORS:
        for node in block.select(selector):
            if any("quote" in cls.lower() for cls in node.get("class", [])):
                continue
            text_len = len(normalize_space(node.get_text(" ", strip=True)))
            if text_len >= 20:
                candidates.append((text_len, node))

    if candidates:
        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]

    return block



def is_file_attachment_anchor(anchor: Tag, page_url: str) -> bool:
    href = normalize_attachment_image_url(urljoin(page_url, anchor.get("href", "")))
    if not href:
        return False
    return "/attachment/" in href and "/attachment/image/" not in href


def extract_file_attachment_label(anchor: Tag, page_url: str) -> str:
    href = normalize_attachment_image_url(urljoin(page_url, anchor.get("href", "")))
    label = normalize_space(anchor.get_text(" ", strip=True))
    if label.startswith("! "):
        label = normalize_space(label[2:])
    if not label:
        label = Path(urlparse(href).path).name
    return label


def find_attachment_row(anchor: Tag, root_node: Tag) -> Tag | None:
    label = extract_file_attachment_label(anchor, page_url=LOGIN_PAGE_URL)
    for parent in [anchor] + [p for p in anchor.parents if isinstance(p, Tag)]:
        if parent is root_node:
            break
        text = normalize_space(parent.get_text(" ", strip=True))
        if not text or label not in text:
            continue
        low = text.lower()
        if "downloads" in low or ATTACHMENT_SIZE_RE.search(text) or "file type:" in low:
            if len(text) <= 300:
                return parent
    return None


def build_attachment_label_from_row(anchor: Tag, row: Tag | None, page_url: str) -> str:
    label = extract_file_attachment_label(anchor, page_url=page_url)
    extras: list[str] = []

    candidates: list[str] = []
    if row is not None:
        row_text = normalize_space(row.get_text(" ", strip=True))
        if row_text:
            candidates.append(row_text)

    parent = anchor.parent if isinstance(anchor.parent, Tag) else None
    if parent is not None:
        parent_text = normalize_space(parent.get_text(" ", strip=True))
        if parent_text:
            candidates.append(parent_text)

    for candidate in candidates:
        for size_match in ATTACHMENT_SIZE_RE.findall(candidate):
            size_text = normalize_space(size_match)
            if size_text and size_text not in extras:
                extras.append(size_text)
        for downloads_match in ATTACHMENT_DOWNLOADS_RE.findall(candidate):
            downloads_text = normalize_space(downloads_match)
            if downloads_text and downloads_text not in extras:
                extras.append(downloads_text)

    return " | ".join([label] + extras) if extras else label


def extract_file_attachment_labels_and_strip(node: Tag | None, page_url: str) -> list[str]:
    if node is None:
        return []

    labels: list[str] = []
    seen: set[tuple[str, str]] = set()

    for anchor in list(node.find_all("a", href=True)):
        if not is_file_attachment_anchor(anchor, page_url=page_url):
            continue

        href = normalize_attachment_image_url(urljoin(page_url, anchor.get("href", "")))
        label = extract_file_attachment_label(anchor, page_url=page_url)
        if not label:
            continue
        low_label = label.lower()
        if low_label in ATTACHMENT_TEXT_BLACKLIST:
            continue

        row = find_attachment_row(anchor, node)
        combined = build_attachment_label_from_row(anchor, row=row, page_url=page_url)
        key = (combined, href)
        if key not in seen:
            seen.add(key)
            labels.append(combined)

        if row is not None:
            row.extract()
        else:
            anchor.extract()

    # remove small icon images and the section heading from the stripped body/signature nodes
    for img in list(node.find_all("img")):
        src = (img.get("data-src") or img.get("data-lazy-src") or img.get("src") or "").strip()
        alt = normalize_space(img.get("alt", ""))
        title = normalize_space(img.get("title", ""))
        full = urljoin(page_url, src) if src else ""
        low_blob = f"{full} {alt} {title}".lower()
        if any(hint in low_blob for hint in ATTACHMENT_ICON_HINTS):
            img.extract()

    for string in list(node.find_all(string=True)):
        if ATTACHMENT_FILE_HEADING_RE.fullmatch(normalize_space(str(string))):
            string.extract()

    return labels


def strip_file_attachment_artifacts_from_text(text: str) -> str:
    cleaned_lines: list[str] = []
    previous_blank = False
    for raw_line in (text or "").splitlines():
        line = normalize_space(raw_line)
        low = line.lower()
        if not line:
            if cleaned_lines and not previous_blank:
                cleaned_lines.append("")
            previous_blank = True
            continue
        if ATTACHMENT_FILE_HEADING_RE.fullmatch(line):
            continue
        if line == "|" or low.startswith("file type:"):
            continue
        if ATTACHMENT_SIZE_RE.fullmatch(line):
            continue
        if ATTACHMENT_DOWNLOADS_RE.fullmatch(line):
            continue
        cleaned_lines.append(line)
        previous_blank = False
    while cleaned_lines and cleaned_lines[0] == "":
        cleaned_lines.pop(0)
    while cleaned_lines and cleaned_lines[-1] == "":
        cleaned_lines.pop()
    return "\n".join(cleaned_lines)


def should_skip_image_tag(img: Tag, page_url: str) -> bool:
    src = img.get("data-src") or img.get("data-lazy-src") or img.get("src") or ""
    full = normalize_attachment_image_url(urljoin(page_url, src)) if src else ""
    alt = normalize_space(img.get("alt", ""))
    title = normalize_space(img.get("title", ""))
    blob = f"{full} {alt} {title}".lower()
    if should_skip_image(full):
        return True
    if any(hint in blob for hint in ATTACHMENT_ICON_HINTS):
        return True
    return False

def is_attachment_anchor(anchor: Tag, page_url: str) -> bool:
    href = normalize_attachment_image_url(urljoin(page_url, anchor.get("href", "")))
    text = normalize_space(anchor.get_text(" ", strip=True))
    low_text = text.lower()

    if not href or "/thread/post/" in href:
        return False
    if low_text in {"reply", "quote", "subscribe"}:
        return False
    if "/attachment/" in href and "/attachment/image/" not in href:
        return True
    if "/attachment/" in href and text and low_text not in ATTACHMENT_TEXT_BLACKLIST:
        return True
    if "download" in href.lower() and text and low_text not in ATTACHMENT_TEXT_BLACKLIST:
        return True
    return False


def extract_attachment_labels(node: Tag | None, page_url: str) -> list[str]:
    if node is None:
        return []

    labels = []
    seen = set()
    for a in node.find_all("a", href=True):
        if not is_attachment_anchor(a, page_url=page_url):
            continue
        if is_file_attachment_anchor(a, page_url=page_url):
            continue
        href = normalize_attachment_image_url(urljoin(page_url, a.get("href", "")))
        label = normalize_space(a.get_text(" ", strip=True))
        if not label:
            label = Path(urlparse(href).path).name
        if not label:
            continue
        low_label = label.lower()
        if low_label in ATTACHMENT_TEXT_BLACKLIST:
            continue
        key = (label, href)
        if key in seen:
            continue
        seen.add(key)
        labels.append(label)
    return labels


def remove_attachment_anchors(node: Tag | None, page_url: str) -> None:
    if node is None:
        return
    for a in list(node.find_all("a", href=True)):
        if is_attachment_anchor(a, page_url=page_url) and not is_file_attachment_anchor(a, page_url=page_url):
            a.extract()


def extract_signature_container(content_node: Tag) -> tuple[Tag, Tag | None]:
    working_node = copy.deepcopy(content_node)
    signature_soup = BeautifulSoup("<div></div>", BS_PARSER)
    signature_holder = signature_soup.div
    has_signature = False

    hr = working_node.find("hr")
    if hr is not None:
        sibling = hr.next_sibling
        while sibling is not None:
            next_sibling = sibling.next_sibling
            if isinstance(sibling, Tag):
                signature_holder.append(copy.deepcopy(sibling))
                sibling.extract()
                has_signature = True
            else:
                text_value = str(sibling)
                if text_value.strip():
                    signature_holder.append(NavigableString(text_value))
                    has_signature = True
                sibling.extract()
            sibling = next_sibling
        hr.extract()

    explicit_signature_nodes = working_node.select("[class*='signature'], [id*='signature']")
    for sig_node in list(explicit_signature_nodes):
        signature_holder.append(copy.deepcopy(sig_node))
        sig_node.extract()
        has_signature = True

    return working_node, signature_holder if has_signature else None



def normalize_multiline_text(text: str) -> str:
    normalized: list[str] = []
    previous_blank = False
    for raw_line in (text or "").splitlines():
        line = normalize_space(raw_line)
        if not line:
            if normalized and not previous_blank:
                normalized.append("")
            previous_blank = True
            continue
        normalized.append(line)
        previous_blank = False

    while normalized and normalized[0] == "":
        normalized.pop(0)
    while normalized and normalized[-1] == "":
        normalized.pop()

    return "\n".join(normalized)


def dedupe_consecutive_lines_preserve_blanks(text: str) -> str:
    deduped: list[str] = []
    previous_key: str | None = None
    for raw_line in (text or "").splitlines():
        line = raw_line.rstrip()
        key = normalize_space(line)
        if key and key == previous_key:
            continue
        deduped.append(line)
        previous_key = key if key else None
    while deduped and deduped[0] == "":
        deduped.pop(0)
    while deduped and deduped[-1] == "":
        deduped.pop()
    return "\n".join(deduped)


def dedupe_all_signature_lines(text: str) -> str:
    output: list[str] = []
    seen: set[str] = set()
    for raw_line in (text or "").splitlines():
        line = raw_line.rstrip()
        key = normalize_space(line)
        if not key:
            if output and output[-1] != "":
                output.append("")
            continue
        if key in seen:
            continue
        seen.add(key)
        output.append(line)
    while output and output[0] == "":
        output.pop(0)
    while output and output[-1] == "":
        output.pop()
    return "\n".join(output)


def extract_post_sections(
    block: Tag,
    page_url: str,
    author: str,
    timestamp: str,
    post_label: str,
) -> tuple[str, str, list[str], str, Tag]:
    content_node = choose_content_node(block)
    body_node, signature_node = extract_signature_container(content_node)

    attachment_labels = []
    attachment_labels.extend(extract_attachment_labels(body_node, page_url=page_url))
    attachment_labels.extend(extract_file_attachment_labels_and_strip(body_node, page_url=page_url))

    if signature_node is not None:
        attachment_labels.extend(extract_attachment_labels(signature_node, page_url=page_url))
        attachment_labels.extend(extract_file_attachment_labels_and_strip(signature_node, page_url=page_url))

    deduped_labels: list[str] = []
    seen_labels: set[str] = set()
    for label in attachment_labels:
        cleaned_label = normalize_space(label)
        if cleaned_label and cleaned_label not in seen_labels:
            seen_labels.add(cleaned_label)
            deduped_labels.append(cleaned_label)

    remove_attachment_anchors(body_node, page_url=page_url)
    remove_attachment_anchors(signature_node, page_url=page_url)

    body_text = strip_file_attachment_artifacts_from_text(
        normalize_multiline_text(
            build_text_from_node(body_node, author=author, timestamp=timestamp, post_label=post_label)
        )
    )
    signature_text = ""
    if signature_node is not None:
        signature_text = dedupe_all_signature_lines(
            dedupe_consecutive_lines_preserve_blanks(
                strip_file_attachment_artifacts_from_text(
                    normalize_multiline_text(
                        build_text_from_node(signature_node, author="", timestamp="Unknown date", post_label="")
                    )
                )
            )
        )

    sections = []
    if body_text:
        sections.append(body_text)
    if deduped_labels:
        sections.append("\n".join(f"Attachment: {label}" for label in deduped_labels))
    if signature_text:
        sections.append("\n".join(f"Sig: {line}" for line in signature_text.splitlines() if normalize_space(line)))

    composed_text = "\n\n".join(section for section in sections if section).strip()
    return body_text, signature_text, deduped_labels, composed_text, content_node


def extract_image_urls(block: Tag, page_url: str) -> list[str]:
    urls = []
    seen = set()

    for img in block.find_all("img"):
        src = img.get("data-src") or img.get("data-lazy-src") or img.get("src")
        if not src:
            continue
        if should_skip_image_tag(img, page_url=page_url):
            continue
        full = normalize_attachment_image_url(urljoin(page_url, src))
        if full not in seen:
            seen.add(full)
            urls.append(full)

    for a in block.find_all("a", href=True):
        href = normalize_attachment_image_url(urljoin(page_url, a["href"]))
        text = normalize_space(a.get_text(" ", strip=True))
        if is_file_attachment_anchor(a, page_url=page_url):
            continue
        if "/attachment/image/" in href or IMAGE_EXT_RE.search(href) or "click to enlarge" in text.lower():
            if should_skip_image(href):
                continue
            if href not in seen:
                seen.add(href)
                urls.append(href)

    return urls


def guess_extension_from_url(url: str) -> str:
    path = urlparse(url).path
    suffix = Path(path).suffix.lower()
    if suffix and len(suffix) <= 5:
        return suffix
    return ".jpg"


def download_image(
    session: requests.Session,
    url: str,
    folder: Path,
    filename_stem: str,
    logger: logging.Logger,
    download_cache: dict[str, str],
) -> tuple[str | None, str]:
    if url in download_cache:
        return download_cache[url], "reused"

    ext = guess_extension_from_url(url)
    filename = safe_filename(f"{filename_stem}{ext}")
    path = folder / filename

    if path.exists():
        rel = f"images/{path.name}"
        download_cache[url] = rel
        return rel, "reused"

    try:
        response = request_with_retries(session, url, logger=logger, stream=False)
        content_type = response.headers.get("Content-Type", "").lower()
        if "html" in content_type:
            logger.warning("Skipping likely non-image response: %s", url)
            return None, "skipped"

        atomic_write_bytes(path, response.content)
        rel = f"images/{path.name}"
        download_cache[url] = rel
        time.sleep(IMAGE_DELAY_SECONDS)
        return rel, "downloaded"
    except Exception as exc:
        logger.warning("Image download failed for %s: %s", url, exc)
        return None, "failed"


def post_validation_reasons(post: dict) -> list[str]:
    reasons = []
    author = normalize_space(post.get("author", ""))
    timestamp = normalize_space(post.get("timestamp", ""))
    post_number = normalize_space(post.get("post_number", ""))
    post_id = normalize_space(post.get("post_id", ""))
    text = normalize_space(post.get("text", ""))
    has_images = bool(post.get("image_urls"))

    strong_signals = 0
    if post_id:
        strong_signals += 1
    if post_number:
        strong_signals += 1
    if timestamp and timestamp != "Unknown date":
        strong_signals += 1

    if strong_signals < 2:
        reasons.append("weak_post_signals")
    if author.lower().startswith("quoting "):
        reasons.append("author_is_quote_header")
    if author in {"Unknown", "Quote"}:
        reasons.append("weak_author")
    if not text and not has_images:
        reasons.append("empty_post")
    if post_number == "" and timestamp == "Unknown date":
        reasons.append("missing_label_and_timestamp")

    return reasons


def is_valid_post(post: dict) -> tuple[bool, list[str]]:
    reasons = post_validation_reasons(post)
    reject_reasons = set(reasons)

    if "empty_post" in reject_reasons:
        return False, reasons
    if "weak_post_signals" in reject_reasons:
        return False, reasons
    if "author_is_quote_header" in reject_reasons and "missing_label_and_timestamp" in reject_reasons:
        return False, reasons
    if "weak_author" in reject_reasons and "missing_label_and_timestamp" in reject_reasons:
        return False, reasons

    return True, reasons


def parse_post(block: Tag, page_num: int, page_url: str) -> dict:
    post_id, post_label, post_url = extract_post_id_and_label(block, page_url=page_url)
    if block.get("data-ff-opener") == "1" and not post_label:
        post_label = "1"
    author = extract_author(block)
    timestamp = extract_timestamp_line(block)
    body_text, signature_text, attachment_labels, text, content_node = extract_post_sections(
        block,
        page_url=page_url,
        author=author,
        timestamp=timestamp,
        post_label=post_label,
    )
    image_urls = extract_image_urls(content_node, page_url=page_url)

    post = {
        "post_id": post_id,
        "post_number": post_label,
        "post_url": post_url,
        "page": page_num,
        "author": author,
        "timestamp": timestamp,
        "text": text,
        "body_text": body_text,
        "signature_text": signature_text,
        "attachment_labels": attachment_labels,
        "image_urls": image_urls,
        "images": [],
        "raw_html": str(block),
    }
    accepted, reasons = is_valid_post(post)
    post["accepted"] = accepted
    post["validation_reasons"] = reasons
    return post


def validate_page(
    page_num: int,
    soup: BeautifulSoup,
    accepted_posts: list[dict],
    rejected_posts: list[dict],
) -> dict:
    expected_labels = extract_expected_post_numbers(soup)
    accepted_labels = [str(post.get("post_number", "")) for post in accepted_posts if post.get("post_number")]

    if page_num == 1:
        if expected_labels and expected_labels[0] != "1":
            expected_labels = ["1"] + expected_labels
        elif not expected_labels:
            expected_labels = ["1"]
    missing_labels = [label for label in expected_labels if label not in accepted_labels]
    extra_unlabelled = sum(1 for post in accepted_posts if not post.get("post_number"))
    unknown_date_posts = sum(1 for post in accepted_posts if post.get("timestamp") == "Unknown date")

    warnings = []
    passed = True

    if expected_labels:
        if len(accepted_posts) != len(expected_labels):
            passed = False
            warnings.append(
                f"expected {len(expected_labels)} labelled posts but accepted {len(accepted_posts)}"
            )
        if page_num == 1 and "1" not in accepted_labels:
            passed = False
            warnings.append("page 1 opener missing")
        if missing_labels:
            passed = False
            warnings.append(f"missing post numbers: {', '.join(missing_labels[:12])}")
        if extra_unlabelled:
            passed = False
            warnings.append(f"{extra_unlabelled} accepted post(s) had no post number")

    if rejected_posts:
        warnings.append(f"rejected {len(rejected_posts)} weak candidate(s)")

    if unknown_date_posts:
        warnings.append(f"{unknown_date_posts} accepted post(s) had Unknown date")

    return {
        "page": page_num,
        "expected_post_numbers": expected_labels,
        "expected_post_count": len(expected_labels),
        "accepted_post_count": len(accepted_posts),
        "rejected_post_count": len(rejected_posts),
        "accepted_post_numbers": accepted_labels,
        "missing_post_numbers": missing_labels,
        "extra_unlabelled_posts": extra_unlabelled,
        "unknown_date_posts": unknown_date_posts,
        "passed": passed,
        "warnings": warnings,
    }


def save_post_snapshot(post: dict, posts_dir: Path) -> None:
    post_key = post["post_id"] or f"page{post['page']}_post{post.get('post_number') or 'unknown'}"
    html_path = posts_dir / f"{safe_filename(post_key)}.html"
    json_path = posts_dir / f"{safe_filename(post_key)}.json"

    atomic_write_text(html_path, post["raw_html"], encoding="utf-8")
    payload = {key: value for key, value in post.items() if key != "raw_html"}
    atomic_write_json(json_path, payload)


def write_assets(assets_dir: Path) -> None:
    css = f"""body{{font-family:Arial,sans-serif;max-width:{EXPORT_CONTENT_MAX_WIDTH_PX}px;margin:2rem auto;padding:0 1.25rem;line-height:1.7;color:#e8e6e3;background:#151515}}
h1,h2,h3{{line-height:1.25;color:#f3efe9}}
a{{color:#9ecbff}}
a:visited{{color:#c8b0ff}}
.meta{{color:#b8b3ac;font-size:.98rem}}
.post{{border-top:1px solid #3a3a3a;padding:1.35rem 0}}
blockquote{{border-left:4px solid #7f6cff;margin:1rem 0;padding:.55rem 1rem;background:#1d1d22;color:#ece8ff}}
img{{max-width:100%;height:auto;display:block;margin:.9rem 0;border:1px solid #333;box-shadow:0 2px 10px rgba(0,0,0,.35)}}
.signature{{margin:1rem 0 0 0;padding-top:.85rem;border-top:1px solid #444;color:#d7d2cb}}
.attachments{{margin:1rem 0 0 0;padding:.35rem 0 .35rem 1rem;border-left:4px solid #888;background:#1c1c1c}}
.attachments p{{margin:.2rem 0}}
pre{{white-space:pre-wrap}}
code{{background:#262626;padding:.1rem .25rem;color:#f1eadb}}"""
    atomic_write_text(assets_dir / "style.css", css, encoding="utf-8")


def render_markdown_image(image_path: str) -> str:
    escaped_path = html.escape(image_path, quote=True)
    return f'<img src="{escaped_path}" alt="Post image" width="{EXPORT_IMAGE_DISPLAY_WIDTH_PX}">'


def post_body_for_export(post: dict) -> str:
    return normalize_multiline_text(post.get("body_text") or post.get("text") or "")


def post_signature_lines(post: dict) -> list[str]:
    signature_text = normalize_multiline_text(post.get("signature_text", ""))
    return [line for line in signature_text.splitlines() if line]


def post_attachment_labels(post: dict) -> list[str]:
    labels = []
    for label in post.get("attachment_labels", []) or []:
        cleaned = normalize_space(label)
        if cleaned:
            labels.append(cleaned)
    return labels


def export_sections(post: dict) -> tuple[str, list[str], list[str]]:
    body_text = normalize_multiline_text(post.get("body_text") or post.get("text") or "")
    attachment_labels = list(post_attachment_labels(post))
    signature_lines = list(post_signature_lines(post))

    body_lines = []
    for raw_line in body_text.splitlines():
        line = raw_line.rstrip()
        clean = normalize_space(line)
        if clean.startswith("Attachment:"):
            label = clean[len("Attachment:"):].strip()
            if label and label not in attachment_labels:
                attachment_labels.append(label)
            continue
        if clean.startswith("Sig:"):
            sig = clean[len("Sig:"):].strip()
            if sig and sig not in signature_lines:
                signature_lines.append(sig)
            continue
        body_lines.append(line)

    body_text = "\n".join(body_lines).strip()

    deduped_attachments = []
    for label in attachment_labels:
        if label not in deduped_attachments:
            deduped_attachments.append(label)

    deduped_sigs = []
    for line in signature_lines:
        clean = normalize_space(line)
        if clean and clean not in deduped_sigs:
            deduped_sigs.append(clean)

    return body_text, deduped_attachments, deduped_sigs


def render_markdown_body_with_images(body_text: str, images: list[str]) -> str:
    parts = []
    image_index = 0

    for raw_line in body_text.splitlines():
        line = raw_line.rstrip()
        if normalize_space(line) == POST_IMAGE_PLACEHOLDER:
            if image_index < len(images):
                parts.append(render_markdown_image(images[image_index]) + "\n\n")
                image_index += 1
            continue
        parts.append(line + "\n")

    if parts and not parts[-1].endswith("\n\n"):
        parts.append("\n")

    while image_index < len(images):
        parts.append(render_markdown_image(images[image_index]) + "\n\n")
        image_index += 1

    return "".join(parts)


def flush_html_buffers(parts: list[str], paragraph_lines: list[str], quote_lines: list[str]) -> None:
    if paragraph_lines:
        for line in paragraph_lines:
            parts.append(f"<p>{html.escape(line)}</p>")
        paragraph_lines.clear()

    if quote_lines:
        parts.append("<blockquote>")
        for line in quote_lines:
            parts.append(f"<p>{html.escape(line)}</p>")
        parts.append("</blockquote>")
        quote_lines.clear()


def render_html_body_with_images(parts: list[str], body_text: str, images: list[str]) -> None:
    image_index = 0
    paragraph_lines: list[str] = []
    quote_lines: list[str] = []

    for raw_line in body_text.splitlines():
        line = raw_line.rstrip()
        norm = normalize_space(line)

        if not norm:
            flush_html_buffers(parts, paragraph_lines, quote_lines)
            continue

        if norm == POST_IMAGE_PLACEHOLDER:
            flush_html_buffers(parts, paragraph_lines, quote_lines)
            if image_index < len(images):
                escaped_img = html.escape(images[image_index], quote=True)
                parts.append(
                    f"<img src='{escaped_img}' alt='post image' loading='lazy' "
                    f"style='width:min(100%, {EXPORT_IMAGE_DISPLAY_WIDTH_PX}px);height:auto;display:block;margin:.75rem 0;'>"
                )
                image_index += 1
            continue

        if line.startswith("> "):
            if paragraph_lines:
                flush_html_buffers(parts, paragraph_lines, quote_lines)
            quote_lines.append(line[2:])
        else:
            if quote_lines:
                flush_html_buffers(parts, paragraph_lines, quote_lines)
            paragraph_lines.append(line)

    flush_html_buffers(parts, paragraph_lines, quote_lines)

    while image_index < len(images):
        escaped_img = html.escape(images[image_index], quote=True)
        parts.append(
            f"<img src='{escaped_img}' alt='post image' loading='lazy' "
            f"style='width:min(100%, {EXPORT_IMAGE_DISPLAY_WIDTH_PX}px);height:auto;display:block;margin:.75rem 0;'>"
        )
        image_index += 1


def export_markdown(posts: list[dict], title: str, source_url: str, out_path: Path) -> None:
    parts = []
    parts.append(f"# {title}\n\n")
    parts.append(f"- Source: {source_url}\n")
    parts.append(f"- Archived at: {datetime.now(timezone.utc).isoformat()}\n")
    parts.append(f"- Total posts: {len(posts)}\n\n")
    parts.append("---\n\n")

    for idx, post in enumerate(posts, start=1):
        label = post["post_number"] or idx
        parts.append(f"## Post {label} — {post['author']}\n\n")
        parts.append(f"**Page:** {post['page']}  \n")
        parts.append(f"**Time:** {post['timestamp']}  \n")
        parts.append(f"**Permalink:** {post['post_url']}\n\n")

        body_text, attachment_labels, signature_lines = export_sections(post)
        if body_text:
            parts.append(render_markdown_body_with_images(body_text, post["images"]))

        if attachment_labels:
            for attachment_label in attachment_labels:
                parts.append(f"Attachment: {attachment_label}\n")
            parts.append("\n")

        if signature_lines:
            parts.append("---\n\n")
            for sig_line in signature_lines:
                parts.append(f"Sig: {sig_line}\n")
            parts.append("\n")

        parts.append("---\n\n")

    atomic_write_text(out_path, "".join(parts), encoding="utf-8")

def export_html(posts: list[dict], title: str, source_url: str, out_path: Path) -> None:
    escaped_title = html.escape(title)
    escaped_source = html.escape(source_url, quote=True)

    parts = [
        "<!doctype html>",
        "<html><head><meta charset='utf-8'>",
        f"<title>{escaped_title}</title>",
        "<link rel='stylesheet' href='assets/style.css'>",
        "</head><body>",
        f"<h1>{escaped_title}</h1>",
        f"<p class='meta'><strong>Source:</strong> <a href='{escaped_source}'>{html.escape(source_url)}</a></p>",
        f"<p class='meta'><strong>Archived at:</strong> {datetime.now(timezone.utc).isoformat()}</p>",
        f"<p class='meta'><strong>Total posts:</strong> {len(posts)}</p>",
    ]

    for idx, post in enumerate(posts, start=1):
        label = post["post_number"] or idx
        post_url = html.escape(post["post_url"], quote=True)
        parts.append("<section class='post'>")
        parts.append(f"<h2>Post {html.escape(str(label))} — {html.escape(post['author'])}</h2>")
        parts.append(f"<p class='meta'><strong>Page:</strong> {html.escape(str(post['page']))}<br>")
        parts.append(f"<strong>Time:</strong> {html.escape(post['timestamp'])}<br>")
        parts.append(f"<strong>Permalink:</strong> <a href='{post_url}'>{html.escape(post['post_url'])}</a></p>")

        body_text, attachment_labels, signature_lines = export_sections(post)
        if body_text:
            render_html_body_with_images(parts, body_text, post["images"])

        if attachment_labels:
            parts.append("<div class='attachments' style='margin:1rem 0 0 0; padding:.35rem 0 .35rem 1rem; border-left:4px solid #888; background:rgba(255,255,255,.03)'>")
            for attachment_label in attachment_labels:
                parts.append(f"<p style='margin:.2rem 0'><strong>Attachment:</strong> {html.escape(attachment_label)}</p>")
            parts.append("</div>")

        if signature_lines:
            parts.append("<div class='signature'>")
            for sig_line in signature_lines:
                parts.append(f"<p><strong>Sig:</strong> {html.escape(sig_line)}</p>")
            parts.append("</div>")

        parts.append("</section>")

    parts.append("</body></html>")
    atomic_write_text(out_path, "\n".join(parts), encoding="utf-8")

def load_existing_posts(json_path: Path) -> list[dict]:
    if not json_path.exists():
        return []
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
        return data.get("posts", [])
    except Exception:
        return []


def save_thread_json(
    posts: list[dict],
    title: str,
    source_url: str,
    start_page: int,
    out_path: Path,
) -> None:
    payload = {
        "title": title,
        "source_url": source_url,
        "start_page": start_page,
        "archived_at": datetime.now(timezone.utc).isoformat(),
        "total_posts": len(posts),
        "posts": [{key: value for key, value in post.items() if key != "raw_html"} for post in posts],
    }
    atomic_write_json(out_path, payload)


def merge_posts(existing: list[dict], new_posts: list[dict]) -> list[dict]:
    seen = set()
    merged = []

    def post_key(post: dict) -> tuple:
        return (
            post.get("post_id") or "",
            post.get("post_url") or "",
            post.get("page") or 0,
            post.get("post_number") or "",
        )

    for post in existing + new_posts:
        key = post_key(post)
        if key in seen:
            continue
        seen.add(key)
        merged.append(post)

    def sort_key(post: dict) -> tuple:
        page = int(post.get("page") or 0)
        try:
            number = int(str(post.get("post_number") or "0").replace(",", ""))
        except Exception:
            number = 0
        return (page, number, post.get("post_id") or "")

    merged.sort(key=sort_key)
    return merged


def page_markers_dir(thread_dir: Path) -> Path:
    return ensure_dir(thread_dir / PAGE_MARKERS_DIRNAME)


def page_marker_path(thread_dir: Path, page_num: int) -> Path:
    return page_markers_dir(thread_dir) / f"page_{page_num:04d}.done.json"


def load_completed_pages_from_markers(thread_dir: Path) -> list[int]:
    pages = []
    for path in page_markers_dir(thread_dir).glob("page_*.done.json"):
        match = re.search(r"page_(\d+)\.done\.json$", path.name)
        if match:
            try:
                pages.append(int(match.group(1)))
            except Exception:
                pass
    return sorted(set(pages))


def infer_last_completed_page_from_posts(existing_posts: list[dict]) -> int:
    pages = []
    for post in existing_posts:
        try:
            pages.append(int(post.get("page") or 0))
        except Exception:
            pass
    return max(pages) if pages else 0


def infer_last_cached_html_page(raw_html_dir: Path) -> int:
    pages = []
    if raw_html_dir.exists():
        for path in raw_html_dir.glob("page_*.html"):
            match = re.search(r"page_(\d+)\.html$", path.name)
            if match:
                try:
                    pages.append(int(match.group(1)))
                except Exception:
                    pass
    return max(pages) if pages else 0


def infer_resume_start_page(
    requested_start_page: int,
    existing_posts: list[dict],
    raw_html_dir: Path,
    state_path: Path,
    thread_dir: Path,
    resume_enabled: bool,
    logger: logging.Logger,
    overlap_start_pages: int = 0,
) -> tuple[int, dict, str]:
    resume_state = load_json_file(state_path)

    if not resume_enabled:
        logger.info("Resume disabled for this run.")
        return requested_start_page, resume_state, "disabled"

    next_page = resume_state.get("next_page")
    if isinstance(next_page, int) and next_page >= requested_start_page:
        logger.info("Resume source: state file -> page %s", next_page)
        return next_page, resume_state, "state"

    completed_pages = load_completed_pages_from_markers(thread_dir)
    if completed_pages:
        inferred = max(completed_pages) + 1
        if inferred >= requested_start_page:
            logger.info("Resume source: page markers -> page %s", inferred)
            return inferred, resume_state, "page_markers"

    last_posts_page = infer_last_completed_page_from_posts(existing_posts)
    if last_posts_page >= requested_start_page:
        inferred = last_posts_page + 1
        logger.info("Resume source: thread.json posts -> page %s", inferred)
        return inferred, resume_state, "thread_json"

    last_cached_page = infer_last_cached_html_page(raw_html_dir)
    if last_cached_page >= requested_start_page:
        logger.info("Resume source: cached HTML fallback -> page %s", last_cached_page)
        return last_cached_page, resume_state, "raw_html"

    if overlap_start_pages > 0 and requested_start_page > 1:
        overlapped = max(1, requested_start_page - overlap_start_pages)
        logger.info("Resume source: requested start page with overlap -> page %s", overlapped)
        return overlapped, resume_state, "requested_with_overlap"

    logger.info("Resume source: requested start page -> page %s", requested_start_page)
    return requested_start_page, resume_state, "requested"


def write_resume_state(
    state_path: Path,
    *,
    base_url: str,
    title: str,
    requested_start_page: int,
    actual_start_page: int,
    last_completed_page: int,
    next_page: int,
    last_page_seen: int | None,
    finished: bool,
    average_seconds_per_page: float | None,
    final_page_verified: bool,
    validation_warning_pages: list[int],
    unknown_date_posts_total: int,
    last_run_summary_path: Path | None = None,
) -> None:
    payload = {
        "base_url": base_url,
        "title": title,
        "requested_start_page": requested_start_page,
        "actual_start_page": actual_start_page,
        "last_completed_page": last_completed_page,
        "next_page": next_page,
        "last_page_seen": last_page_seen,
        "finished": finished,
        "average_seconds_per_page": average_seconds_per_page,
        "final_page_verified": final_page_verified,
        "validation_warning_pages": validation_warning_pages,
        "unknown_date_posts_total": unknown_date_posts_total,
        "last_run_summary_path": str(last_run_summary_path) if last_run_summary_path else "",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    atomic_write_json(state_path, payload)


def write_page_marker(
    thread_dir: Path,
    *,
    page_num: int,
    page_url: str,
    title: str,
    new_posts_count: int,
    new_images_downloaded: int,
    new_images_reused: int,
    used_cached_html: bool,
    validation: dict,
    attempts: int,
) -> None:
    payload = {
        "page": page_num,
        "page_url": page_url,
        "title": title,
        "new_posts_count": new_posts_count,
        "new_images_downloaded": new_images_downloaded,
        "new_images_reused": new_images_reused,
        "used_cached_html": used_cached_html,
        "validation": validation,
        "attempts": attempts,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    atomic_write_json(page_marker_path(thread_dir, page_num), payload)


def build_progress_bar(initial_done: int, total_pages: int | None, debug: bool = False) -> tqdm:
    if debug:
        bar_format = "{l_bar}{bar}| {n_fmt}/{total_fmt} pages [{percentage:3.0f}%] {postfix}"
    else:
        bar_format = "Archive progress: {bar}| {n_fmt}/{total_fmt} pages [{percentage:3.0f}%] | {postfix}"

    return tqdm(
        total=total_pages,
        initial=initial_done,
        desc="" if not debug else "Archive progress",
        unit="page",
        leave=True,
        file=sys.stdout,
        dynamic_ncols=True,
        mininterval=PROGRESS_MIN_INTERVAL_SECONDS,
        miniters=1,
        smoothing=0,
        position=0,
        bar_format=bar_format,
    )


def format_hms(seconds: float | int | None) -> str:
    if seconds is None:
        return "?"
    seconds = max(0, int(round(seconds)))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_eta_clock(seconds_remaining: float | None) -> str:
    if seconds_remaining is None:
        return "?"
    eta_dt = datetime.now() + timedelta(seconds=max(0, seconds_remaining))
    return eta_dt.strftime("%H:%M")


def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def weighted_recent_average(values: list[float]) -> float | None:
    if not values:
        return None
    weights = list(range(1, len(values) + 1))
    weighted_sum = sum(v * w for v, w in zip(values, weights))
    return weighted_sum / sum(weights)


def choose_page_seconds_estimate(page_durations: list[float], historical_avg_seconds: float | None) -> float:
    if not page_durations and historical_avg_seconds:
        return historical_avg_seconds
    if not page_durations:
        return INITIAL_ESTIMATED_SECONDS_PER_PAGE

    recent = page_durations[-ROLLING_AVG_WINDOW:]
    recent_weighted = weighted_recent_average(recent) or recent[-1]
    recent_median = median(recent)

    estimate = (recent_weighted * 0.70) + (recent_median * 0.20)
    if historical_avg_seconds:
        estimate = (estimate * 0.85) + (historical_avg_seconds * 0.15)

    return max(1.0, estimate)


def determine_full_total_pages(requested_start_page: int, last_page_seen: int | None) -> int | None:
    if last_page_seen is None or last_page_seen < requested_start_page:
        return None
    return last_page_seen - requested_start_page + 1


def determine_progress_total_pages(
    *,
    requested_start_page: int,
    actual_start_page: int,
    last_page_seen: int | None,
    max_pages: int | None,
) -> int | None:
    if max_pages is not None:
        if last_page_seen is None:
            return max_pages
        remaining_from_actual = max(0, last_page_seen - actual_start_page + 1)
        return min(max_pages, remaining_from_actual)
    return determine_full_total_pages(requested_start_page, last_page_seen)


def update_progress_display(
    pbar: tqdm,
    *,
    session_elapsed_seconds: float,
    pages_done_this_run: int,
    progress_done: int,
    progress_total: int | None,
    page_durations: list[float],
    historical_avg_seconds: float | None,
    full_remaining_pages: int | None = None,
) -> float | None:
    if progress_total is None:
        pbar.set_postfix_str(
            f"Elapsed {format_hms(session_elapsed_seconds)} | Left warming up | ETA ?",
            refresh=True,
        )
        return None

    remaining_pages = max(0, progress_total - progress_done)
    estimate_seconds = choose_page_seconds_estimate(page_durations, historical_avg_seconds)
    remaining_seconds = remaining_pages * estimate_seconds

    if remaining_pages == 0:
        postfix = f"Elapsed {format_hms(session_elapsed_seconds)} | Left 00:00:00 | ETA now"
        if full_remaining_pages:
            postfix += f" | Full ~{format_hms(full_remaining_pages * estimate_seconds)}"
        pbar.set_postfix_str(postfix, refresh=True)
        return estimate_seconds

    left_text = "~" + format_hms(remaining_seconds)
    eta_text = "~" + format_eta_clock(remaining_seconds)

    postfix = f"Elapsed {format_hms(session_elapsed_seconds)} | Left {left_text} | ETA {eta_text}"
    if full_remaining_pages is not None and full_remaining_pages > remaining_pages:
        postfix += f" | Full ~{format_hms(full_remaining_pages * estimate_seconds)}"

    pbar.set_postfix_str(postfix, refresh=True)
    return estimate_seconds

def count_local_images(images_dir: Path) -> int:
    if not images_dir.exists():
        return 0
    return sum(1 for path in images_dir.iterdir() if path.is_file() and not path.name.endswith(PARTIAL_FILE_SUFFIX))


def verify_final_page_completion(
    *,
    last_page_seen: int | None,
    last_completed_page: int,
    final_page_validation: dict | None,
) -> tuple[bool, str]:
    if last_page_seen is None:
        return False, "last page unknown"
    if last_completed_page < last_page_seen:
        return False, "did not reach detected last page"
    if final_page_validation is None:
        return False, "final page validation missing"
    if not final_page_validation.get("passed"):
        return False, "final page validation failed"
    if final_page_validation.get("accepted_post_count", 0) <= 0:
        return False, "final page contained no accepted posts"
    return True, "final page validated"


def build_run_summary(
    *,
    title: str,
    base_url: str,
    thread_dir: Path,
    requested_start_page: int,
    actual_start_page: int,
    last_completed_page_this_session: int,
    next_page_for_resume: int,
    last_page_seen: int | None,
    finished_archive: bool,
    interrupted: bool,
    resume_source: str,
    max_pages_requested: int | None,
    progress_total_pages: int | None,
    pages_completed_this_run: int,
    new_posts_saved_this_run: int,
    images_downloaded_this_run: int,
    images_reused_this_run: int,
    cached_html_pages_reused_this_run: int,
    partial_files_cleaned_on_startup: int,
    total_posts_saved: int,
    total_local_images: int,
    average_seconds_per_page: float | None,
    validation_warning_pages: list[int],
    validation_retry_pages: list[int],
    validation_failures_this_run: int,
    rejected_candidates_this_run: int,
    unknown_date_posts_this_run: int,
    final_page_verified: bool,
    final_page_verification_reason: str,
    final_page_validation: dict | None,
) -> dict:
    return {
        "thread_title": title,
        "thread_url": base_url,
        "output_folder": str(thread_dir.resolve()),
        "requested_start_page": requested_start_page,
        "actual_start_page": actual_start_page,
        "last_completed_page_this_session": last_completed_page_this_session,
        "next_page_for_resume": next_page_for_resume,
        "detected_last_page": last_page_seen,
        "finished_archive": finished_archive,
        "interrupted": interrupted,
        "resume_source": resume_source,
        "max_pages_requested": max_pages_requested,
        "progress_total_pages": progress_total_pages,
        "pages_completed_this_run": pages_completed_this_run,
        "new_posts_saved_this_run": new_posts_saved_this_run,
        "images_downloaded_this_run": images_downloaded_this_run,
        "images_reused_this_run": images_reused_this_run,
        "cached_html_pages_reused_this_run": cached_html_pages_reused_this_run,
        "partial_files_cleaned_on_startup": partial_files_cleaned_on_startup,
        "total_posts_saved": total_posts_saved,
        "total_local_images": total_local_images,
        "average_seconds_per_page": average_seconds_per_page,
        "validation_warning_pages": validation_warning_pages,
        "validation_retry_pages": validation_retry_pages,
        "validation_failures_this_run": validation_failures_this_run,
        "rejected_candidates_this_run": rejected_candidates_this_run,
        "unknown_date_posts_this_run": unknown_date_posts_this_run,
        "final_page_verified": final_page_verified,
        "final_page_verification_reason": final_page_verification_reason,
        "final_page_validation": final_page_validation or {},
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def print_session_summary(summary: dict, summary_path: Path) -> None:
    heading = "Session summary (interrupted)" if summary.get("interrupted") else "Session summary"
    print("\n" + heading)
    print("-" * 60)
    print(f"Thread title: {summary.get('thread_title') or 'Unknown'}")
    print(f"Thread URL: {summary['thread_url']}")
    print(f"Output folder: {summary['output_folder']}")
    print(f"Requested start page: {summary['requested_start_page']}")
    print(f"Actual start page: {summary['actual_start_page']}")
    print(f"Last completed page this session: {summary['last_completed_page_this_session']}")
    print(f"Next page for resume: {summary['next_page_for_resume']}")
    print(f"Detected last page: {summary['detected_last_page']}")
    print(f"Finished archive: {summary['finished_archive']}")
    print(f"Resume source: {summary['resume_source']}")
    if summary.get("max_pages_requested") is not None:
        print(f"Run scope pages: {summary.get('progress_total_pages')} (max_pages={summary.get('max_pages_requested')})")
    avg_spp = summary.get("average_seconds_per_page")
    if avg_spp:
        print(f"Average seconds per page: {avg_spp:.2f}")
    print(f"Final page verified: {summary['final_page_verified']} ({summary['final_page_verification_reason']})")

    print("\nThis run")
    print(f"  Pages completed: {summary['pages_completed_this_run']}")
    print(f"  New posts saved: {summary['new_posts_saved_this_run']}")
    print(f"  Images downloaded: {summary['images_downloaded_this_run']}")
    print(f"  Images reused: {summary['images_reused_this_run']}")
    print(f"  Cached HTML pages reused: {summary['cached_html_pages_reused_this_run']}")
    print(f"  Partial files cleaned: {summary['partial_files_cleaned_on_startup']}")
    print(f"  Validation warning pages: {summary['validation_warning_pages']}")
    print(f"  Validation retry pages: {summary['validation_retry_pages']}")
    print(f"  Validation failures this run: {summary['validation_failures_this_run']}")
    print(f"  Rejected weak candidates: {summary['rejected_candidates_this_run']}")
    print(f"  Accepted posts with Unknown date: {summary['unknown_date_posts_this_run']}")

    print("\nArchive totals")
    print(f"  Total posts saved: {summary['total_posts_saved']}")
    print(f"  Total local images: {summary['total_local_images']}")

    print(f"\nSummary file: {summary_path.resolve()}")
    print("-" * 60)

def parse_int_range_tokens(spec: str, *, allow_hash_prefix: bool = False) -> list[int]:
    values: set[int] = set()
    if not spec:
        return []

    tokens = re.split(r"[\s,]+", str(spec).strip())
    for raw in tokens:
        token = raw.strip()
        if not token:
            continue
        if allow_hash_prefix and token.startswith("#"):
            token = token[1:].strip()
        if not token:
            continue

        if "-" in token:
            left, right = token.split("-", 1)
            left = left.strip()
            right = right.strip()
            if allow_hash_prefix and left.startswith("#"):
                left = left[1:].strip()
            if allow_hash_prefix and right.startswith("#"):
                right = right[1:].strip()
            if left.isdigit() and right.isdigit():
                start = int(left)
                end = int(right)
                lower = min(start, end)
                upper = max(start, end)
                for value in range(lower, upper + 1):
                    if value >= 1:
                        values.add(value)
            continue

        if token.isdigit():
            value = int(token)
            if value >= 1:
                values.add(value)

    return sorted(values)


def parse_page_spec(spec: str) -> list[int]:
    return parse_int_range_tokens(spec, allow_hash_prefix=False)


def parse_posts_spec(spec: str) -> list[int]:
    return parse_int_range_tokens(spec, allow_hash_prefix=True)


def load_posts_spec_file(path_spec: str | None) -> list[int]:
    cleaned = normalize_space(path_spec or "")
    if not cleaned:
        return []
    path = Path(cleaned)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Could not find posts file: {path}")
    content = path.read_text(encoding="utf-8", errors="replace")
    return parse_posts_spec(content)


def replace_posts_for_pages(existing_posts: list[dict], replacement_posts: list[dict], target_pages: list[int]) -> list[dict]:
    target_set = {int(page) for page in target_pages}
    kept_posts = []
    for post in existing_posts:
        try:
            page = int(post.get("page") or 0)
        except Exception:
            page = 0
        if page not in target_set:
            kept_posts.append(post)
    return merge_posts(kept_posts, replacement_posts)


def determine_repair_pages(
    *,
    repair_pages_spec: str | None,
    repair_validation_warnings: bool,
    state_path: Path,
    summary_path: Path,
    logger: logging.Logger,
) -> list[int]:
    pages = set(parse_page_spec(repair_pages_spec or ""))

    if repair_validation_warnings:
        resume_state = load_json_file(state_path)
        summary_state = load_json_file(summary_path)
        warning_pages = resume_state.get("validation_warning_pages") or summary_state.get("validation_warning_pages") or []
        for page in warning_pages:
            try:
                page_num = int(page)
            except Exception:
                continue
            if page_num >= 1:
                pages.add(page_num)

    selected = sorted(pages)
    if selected:
        logger.info("Repair mode selected page(s): %s", ", ".join(str(page) for page in selected))
    return selected


def build_repair_summary(
    *,
    title: str,
    base_url: str,
    thread_dir: Path,
    pages_requested: list[int],
    pages_processed: list[int],
    pages_repaired_cleanly: list[int],
    pages_still_warning: list[int],
    posts_added_to_archive: int,
    posts_replaced_in_archive: int,
    images_downloaded_this_run: int,
    images_reused_this_run: int,
    partial_files_cleaned_on_startup: int,
    total_posts_saved: int,
    total_local_images: int,
) -> dict:
    return {
        "mode": "repair",
        "thread_title": title,
        "thread_url": base_url,
        "output_folder": str(thread_dir.resolve()),
        "pages_requested": pages_requested,
        "pages_processed": pages_processed,
        "pages_repaired_cleanly": pages_repaired_cleanly,
        "pages_still_warning": pages_still_warning,
        "posts_added_to_archive": posts_added_to_archive,
        "posts_replaced_in_archive": posts_replaced_in_archive,
        "images_downloaded_this_run": images_downloaded_this_run,
        "images_reused_this_run": images_reused_this_run,
        "partial_files_cleaned_on_startup": partial_files_cleaned_on_startup,
        "total_posts_saved": total_posts_saved,
        "total_local_images": total_local_images,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def print_repair_summary(summary: dict, summary_path: Path) -> None:
    print("\nRepair summary")
    print("-" * 60)
    print(f"Thread title: {summary.get('thread_title') or 'Unknown'}")
    print(f"Thread URL: {summary['thread_url']}")
    print(f"Output folder: {summary['output_folder']}")
    print(f"Pages requested: {summary['pages_requested']}")
    print(f"Pages processed: {summary['pages_processed']}")
    print(f"Pages repaired cleanly: {summary['pages_repaired_cleanly']}")
    print(f"Pages still warning: {summary['pages_still_warning']}")
    print(f"Posts added to archive: {summary['posts_added_to_archive']}")
    print(f"Posts replaced in archive: {summary['posts_replaced_in_archive']}")
    print(f"Images downloaded: {summary['images_downloaded_this_run']}")
    print(f"Images reused: {summary['images_reused_this_run']}")
    print(f"Partial files cleaned: {summary['partial_files_cleaned_on_startup']}")
    print(f"Total posts saved: {summary['total_posts_saved']}")
    print(f"Total local images: {summary['total_local_images']}")
    print(f"Summary file: {summary_path.resolve()}")
    print("-" * 60)


def repair_archive_pages(
    base_url: str,
    start_page: int = 1,
    username: str = "",
    password: str = "",
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    force: bool = True,
    debug: bool = False,
    repair_pages_spec: str | None = None,
    repair_validation_warnings: bool = False,
) -> Path:
    base_url = normalize_thread_url(base_url)

    slug = slugify(base_url.rstrip("/").split("/")[-1])
    thread_dir = ensure_dir(output_root / slug)
    raw_html_dir = ensure_dir(thread_dir / "raw_html")
    posts_dir = ensure_dir(thread_dir / "posts")
    images_dir = ensure_dir(thread_dir / "images")
    assets_dir = ensure_dir(thread_dir / "assets")
    page_markers_dir(thread_dir)

    state_path = thread_dir / RESUME_STATE_FILENAME
    summary_path = thread_dir / LAST_RUN_SUMMARY_FILENAME
    repair_summary_path = thread_dir / "repair_summary.json"
    thread_json_path = thread_dir / "thread.json"

    write_assets(assets_dir)
    logger = setup_logger(thread_dir / "scrape.log", debug=debug)
    partial_files_cleaned = cleanup_partial_files(thread_dir, logger)

    logger.info("Repair mode active.")
    logger.info("Thread URL: %s", base_url)
    logger.info("Output folder: %s", thread_dir.resolve())
    logger.info("Username supplied: %s", bool(username))
    logger.info("Password supplied: %s", bool(password))

    pages_to_repair = determine_repair_pages(
        repair_pages_spec=repair_pages_spec,
        repair_validation_warnings=repair_validation_warnings,
        state_path=state_path,
        summary_path=summary_path,
        logger=logger,
    )
    if not pages_to_repair:
        print("No repair pages selected. Use --repair-pages or --repair-validation-warnings.")
        return thread_dir

    session = requests.Session()
    session.headers.update(HEADERS)
    login_if_requested(session, username=username, password=password, logger=logger)

    existing_posts = load_existing_posts(thread_json_path)
    all_posts = list(existing_posts)

    resume_state = load_json_file(state_path)
    title = resume_state.get("title") or load_json_file(thread_json_path).get("title") or "Forex Factory Thread"
    saved_last_page_seen = resume_state.get("last_page_seen")
    try:
        saved_last_page_seen = int(saved_last_page_seen) if saved_last_page_seen is not None else None
    except Exception:
        saved_last_page_seen = None

    historical_avg_seconds = resume_state.get("average_seconds_per_page")
    try:
        historical_avg_seconds = float(historical_avg_seconds) if historical_avg_seconds is not None else None
    except Exception:
        historical_avg_seconds = None

    validation_warning_pages = sorted(set(int(p) for p in (resume_state.get("validation_warning_pages") or []) if str(p).isdigit()))
    unknown_date_posts_total = int(resume_state.get("unknown_date_posts_total") or 0)
    final_page_verified = bool(resume_state.get("final_page_verified"))

    download_cache: dict[str, str] = {}
    posts_added_to_archive = 0
    posts_replaced_in_archive = 0
    images_downloaded_this_run = 0
    images_reused_this_run = 0
    processed_pages: list[int] = []
    repaired_cleanly: list[int] = []
    still_warning: list[int] = []

    for page in pages_to_repair:
        page_url = get_page_url(base_url, page)
        raw_html_path = raw_html_dir / f"page_{page:04d}.html"
        logger.info("Repairing page %s: %s", page, page_url)

        page_result = None
        attempts = 0

        while attempts <= PAGE_VALIDATION_RETRY_LIMIT:
            current_force = force or attempts > 0
            page_result = collect_page_result(
                session=session,
                page=page,
                page_url=page_url,
                raw_html_path=raw_html_path,
                logger=logger,
                force=current_force,
                seen_post_ids=set(),
                existing_posts_by_id={},
            )
            title = title or page_result["title"]
            if page_result["last_page_seen"]:
                saved_last_page_seen = page_result["last_page_seen"]

            validation = page_result["validation"]
            if validation.get("passed") or attempts >= PAGE_VALIDATION_RETRY_LIMIT:
                break

            attempts += 1
            logger.warning(
                "Repair page %s validation failed, retrying with fresh HTML. Warnings: %s",
                page,
                "; ".join(validation.get("warnings", [])),
            )

        if page_result is None:
            logger.warning("Repair page %s produced no result.", page)
            continue

        validation = page_result["validation"]
        if validation.get("passed"):
            if page in validation_warning_pages:
                validation_warning_pages.remove(page)
            repaired_cleanly.append(page)
        else:
            if page not in validation_warning_pages:
                validation_warning_pages.append(page)
            still_warning.append(page)
            logger.warning("Repair page %s still failed validation: %s", page, "; ".join(validation.get("warnings", [])))

        existing_page_posts = [post for post in all_posts if int(post.get("page") or 0) == page]
        existing_page_ids = {post.get("post_id") for post in existing_page_posts if post.get("post_id")}
        existing_page_keys = {
            (
                str(post.get("post_number") or ""),
                normalize_space(post.get("author", "")),
                normalize_space(post.get("timestamp", "")),
            )
            for post in existing_page_posts
        }

        repaired_posts = []
        page_images_downloaded = 0
        page_images_reused = 0

        for post in page_result["accepted_posts"]:
            post = copy.deepcopy(post)
            image_paths = []
            for idx, img_url in enumerate(post["image_urls"], start=1):
                stem = f"post_{post['post_id'] or post['post_number'] or page}_{idx:02d}"
                rel_path, status = download_image(
                    session=session,
                    url=img_url,
                    folder=images_dir,
                    filename_stem=stem,
                    logger=logger,
                    download_cache=download_cache,
                )
                if rel_path:
                    image_paths.append(rel_path)
                if status == "downloaded":
                    page_images_downloaded += 1
                elif status == "reused":
                    page_images_reused += 1

            post["images"] = image_paths
            save_post_snapshot(post, posts_dir)
            repaired_posts.append(post)

        page_added = 0
        page_replaced = 0
        for post in repaired_posts:
            post_id = post.get("post_id")
            key = (
                str(post.get("post_number") or ""),
                normalize_space(post.get("author", "")),
                normalize_space(post.get("timestamp", "")),
            )
            if post_id and post_id not in existing_page_ids:
                page_added += 1
            elif key not in existing_page_keys:
                page_added += 1
            else:
                page_replaced += 1

        posts_added_to_archive += page_added
        posts_replaced_in_archive += page_replaced
        images_downloaded_this_run += page_images_downloaded
        images_reused_this_run += page_images_reused
        unknown_date_posts_total += validation.get("unknown_date_posts", 0)

        all_posts = replace_posts_for_pages(all_posts, repaired_posts, [page])
        save_thread_json(all_posts, title=title, source_url=base_url, start_page=start_page, out_path=thread_json_path)
        export_markdown(all_posts, title=title, source_url=base_url, out_path=thread_dir / "thread.md")
        export_html(all_posts, title=title, source_url=base_url, out_path=thread_dir / "thread.html")

        write_page_marker(
            thread_dir,
            page_num=page,
            page_url=page_url,
            title=title,
            new_posts_count=len(repaired_posts),
            new_images_downloaded=page_images_downloaded,
            new_images_reused=page_images_reused,
            used_cached_html=page_result["used_cached_html"],
            validation=validation,
            attempts=attempts + 1,
        )
        processed_pages.append(page)

    next_page = int(resume_state.get("next_page") or max((int(p.get("page") or 0) for p in all_posts), default=0) + 1)
    last_completed_page = int(resume_state.get("last_completed_page") or max((int(p.get("page") or 0) for p in all_posts), default=0))
    finished = bool(resume_state.get("finished"))
    requested_start_page = int(resume_state.get("requested_start_page") or start_page)
    actual_start_page = int(resume_state.get("actual_start_page") or start_page)

    write_resume_state(
        state_path,
        base_url=base_url,
        title=title or "Forex Factory Thread",
        requested_start_page=requested_start_page,
        actual_start_page=actual_start_page,
        last_completed_page=last_completed_page,
        next_page=next_page,
        last_page_seen=saved_last_page_seen,
        finished=finished,
        average_seconds_per_page=historical_avg_seconds,
        final_page_verified=final_page_verified,
        validation_warning_pages=sorted(validation_warning_pages),
        unknown_date_posts_total=unknown_date_posts_total,
        last_run_summary_path=summary_path,
    )

    summary = build_repair_summary(
        title=title or "Forex Factory Thread",
        base_url=base_url,
        thread_dir=thread_dir,
        pages_requested=pages_to_repair,
        pages_processed=processed_pages,
        pages_repaired_cleanly=repaired_cleanly,
        pages_still_warning=still_warning,
        posts_added_to_archive=posts_added_to_archive,
        posts_replaced_in_archive=posts_replaced_in_archive,
        images_downloaded_this_run=images_downloaded_this_run,
        images_reused_this_run=images_reused_this_run,
        partial_files_cleaned_on_startup=partial_files_cleaned,
        total_posts_saved=len(all_posts),
        total_local_images=count_local_images(images_dir),
    )
    atomic_write_json(repair_summary_path, summary)
    print_repair_summary(summary, repair_summary_path)
    print(f"Saved to: {thread_dir.resolve()}")
    return thread_dir


def collect_page_result(
    *,
    session: requests.Session,
    page: int,
    page_url: str,
    raw_html_path: Path,
    logger: logging.Logger,
    force: bool,
    seen_post_ids: set[str],
    existing_posts_by_id: dict[str, dict],
) -> dict:
    html, used_cached_html = fetch_html(
        session=session,
        page_url=page_url,
        raw_html_path=raw_html_path,
        logger=logger,
        force=force,
    )
    soup = BeautifulSoup(html, BS_PARSER)
    title = parse_thread_title(soup)
    last_page_seen = parse_last_page(soup, current_page=page, current_page_url=page_url)
    blocks = detect_post_blocks(soup, page_num=page)

    accepted_posts = []
    new_posts = []
    rejected_posts = []
    first_post_id = None

    for block in blocks:
        post = parse_post(block, page_num=page, page_url=page_url)

        if not first_post_id:
            first_post_id = post["post_id"] or post["post_url"]

        if not post.get("accepted"):
            rejected_posts.append(post)
            continue

        accepted_posts.append(post)

        post_id = post.get("post_id")
        if post_id and post_id in seen_post_ids:
            continue

        new_posts.append(copy.deepcopy(post))

    validation = validate_page(page_num=page, soup=soup, accepted_posts=accepted_posts, rejected_posts=rejected_posts)

    return {
        "html": html,
        "used_cached_html": used_cached_html,
        "soup": soup,
        "title": title,
        "last_page_seen": last_page_seen,
        "blocks_count": len(blocks),
        "accepted_posts": accepted_posts,
        "new_posts": new_posts,
        "rejected_posts": rejected_posts,
        "validation": validation,
        "first_post_id": first_post_id,
    }


def scrape_thread(
    base_url: str,
    start_page: int = 1,
    username: str = "",
    password: str = "",
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    max_pages: int | None = None,
    force: bool = False,
    debug: bool = False,
    resume_enabled: bool = True,
    overlap_start_pages: int = DEFAULT_OVERLAP_START_PAGES,
) -> Path:
    base_url = normalize_thread_url(base_url)

    slug = slugify(base_url.rstrip("/").split("/")[-1])
    thread_dir = ensure_dir(output_root / slug)
    raw_html_dir = ensure_dir(thread_dir / "raw_html")
    posts_dir = ensure_dir(thread_dir / "posts")
    images_dir = ensure_dir(thread_dir / "images")
    assets_dir = ensure_dir(thread_dir / "assets")
    page_markers_dir(thread_dir)

    state_path = thread_dir / RESUME_STATE_FILENAME
    summary_path = thread_dir / LAST_RUN_SUMMARY_FILENAME
    thread_json_path = thread_dir / "thread.json"

    write_assets(assets_dir)
    logger = setup_logger(thread_dir / "scrape.log", debug=debug)
    partial_files_cleaned = cleanup_partial_files(thread_dir, logger)

    logger.info("Thread URL: %s", base_url)
    logger.info("Requested start page: %s", start_page)
    logger.info("Username supplied: %s", bool(username))
    logger.info("Password supplied: %s", bool(password))
    logger.info("Output folder: %s", thread_dir.resolve())

    session = requests.Session()
    session.headers.update(HEADERS)
    login_if_requested(session, username=username, password=password, logger=logger)

    existing_posts = load_existing_posts(thread_json_path)
    existing_posts_by_id = {p.get("post_id"): p for p in existing_posts if p.get("post_id")}

    actual_start_page, resume_state, resume_source = infer_resume_start_page(
        requested_start_page=start_page,
        existing_posts=existing_posts,
        raw_html_dir=raw_html_dir,
        state_path=state_path,
        thread_dir=thread_dir,
        resume_enabled=resume_enabled and not force,
        logger=logger,
        overlap_start_pages=overlap_start_pages,
    )

    requested_start_page = start_page
    completed_before_run = max(0, actual_start_page - requested_start_page)

    saved_last_page_seen = resume_state.get("last_page_seen")
    try:
        saved_last_page_seen = int(saved_last_page_seen) if saved_last_page_seen is not None else None
    except Exception:
        saved_last_page_seen = None

    full_total_pages = determine_full_total_pages(requested_start_page, saved_last_page_seen)
    progress_total_pages = determine_progress_total_pages(
        requested_start_page=requested_start_page,
        actual_start_page=actual_start_page,
        last_page_seen=saved_last_page_seen,
        max_pages=max_pages,
    )

    if resume_state.get("finished") and saved_last_page_seen and actual_start_page > saved_last_page_seen:
        average_seconds_per_page = resume_state.get("average_seconds_per_page")
        final_page_verified = bool(resume_state.get("final_page_verified"))
        summary = build_run_summary(
            title=resume_state.get("title") or "Forex Factory Thread",
            base_url=base_url,
            thread_dir=thread_dir,
            requested_start_page=requested_start_page,
            actual_start_page=actual_start_page,
            last_completed_page_this_session=saved_last_page_seen,
            next_page_for_resume=actual_start_page,
            last_page_seen=saved_last_page_seen,
            finished_archive=True,
            interrupted=False,
            resume_source=resume_source,
            max_pages_requested=max_pages,
            progress_total_pages=determine_progress_total_pages(
                requested_start_page=requested_start_page,
                actual_start_page=actual_start_page,
                last_page_seen=saved_last_page_seen,
                max_pages=max_pages,
            ),
            pages_completed_this_run=0,
            new_posts_saved_this_run=0,
            images_downloaded_this_run=0,
            images_reused_this_run=0,
            cached_html_pages_reused_this_run=0,
            partial_files_cleaned_on_startup=partial_files_cleaned,
            total_posts_saved=len(existing_posts),
            total_local_images=count_local_images(images_dir),
            average_seconds_per_page=average_seconds_per_page,
            validation_warning_pages=resume_state.get("validation_warning_pages", []),
            validation_retry_pages=[],
            validation_failures_this_run=0,
            rejected_candidates_this_run=0,
            unknown_date_posts_this_run=0,
            final_page_verified=final_page_verified,
            final_page_verification_reason="already complete",
            final_page_validation={},
        )
        atomic_write_json(summary_path, summary)
        print_session_summary(summary, summary_path)
        print(f"Saved to: {thread_dir.resolve()}")
        return thread_dir

    seen_post_ids = {post.get("post_id") for post in existing_posts if post.get("post_id")}
    all_posts = list(existing_posts)

    page = actual_start_page
    title = resume_state.get("title") or ""
    last_page_seen = saved_last_page_seen
    previous_first_post_id = None
    page_durations: list[float] = []

    historical_avg_seconds = resume_state.get("average_seconds_per_page")
    try:
        historical_avg_seconds = float(historical_avg_seconds) if historical_avg_seconds is not None else None
    except Exception:
        historical_avg_seconds = None

    new_posts_saved_this_run = 0
    images_downloaded_this_run = 0
    images_reused_this_run = 0
    cached_html_pages_reused_this_run = 0
    pages_completed_this_run = 0
    interrupted = False
    finished_archive = False
    last_completed_page_runtime = actual_start_page - 1
    validation_warning_pages = list(resume_state.get("validation_warning_pages", []))
    validation_retry_pages: list[int] = []
    validation_failures_this_run = 0
    rejected_candidates_this_run = 0
    unknown_date_posts_this_run = 0
    final_page_verified = False
    final_page_verification_reason = "not reached"
    final_page_validation = None

    download_cache: dict[str, str] = {}
    started_at = time.time()
    progress_initial_done = 0 if max_pages is not None else completed_before_run
    pbar = build_progress_bar(initial_done=progress_initial_done, total_pages=progress_total_pages)
    update_progress_display(
        pbar,
        session_elapsed_seconds=0,
        pages_done_this_run=0,
        progress_done=progress_initial_done,
        progress_total=progress_total_pages,
        page_durations=page_durations,
        historical_avg_seconds=historical_avg_seconds,
        full_remaining_pages=full_total_pages if max_pages is not None else None,
    )

    try:
        while True:
            if max_pages is not None and pages_completed_this_run >= max_pages:
                logger.info("Reached max_pages=%s; stopping.", max_pages)
                break

            page_started_at = time.time()
            page_url = get_page_url(base_url, page)
            raw_html_path = raw_html_dir / f"page_{page:04d}.html"
            logger.info("Fetching page %s: %s", page, page_url)

            page_result = None
            attempts = 0

            while attempts <= PAGE_VALIDATION_RETRY_LIMIT:
                current_force = force or attempts > 0
                page_result = collect_page_result(
                    session=session,
                    page=page,
                    page_url=page_url,
                    raw_html_path=raw_html_path,
                    logger=logger,
                    force=current_force,
                    seen_post_ids=seen_post_ids,
                    existing_posts_by_id=existing_posts_by_id,
                )

                if page_result["used_cached_html"]:
                    cached_html_pages_reused_this_run += 1

                if not title:
                    title = page_result["title"]
                if page_result["last_page_seen"]:
                    last_page_seen = page_result["last_page_seen"]
                    full_total_pages = determine_full_total_pages(requested_start_page, last_page_seen)
                    progress_total_pages = determine_progress_total_pages(
                        requested_start_page=requested_start_page,
                        actual_start_page=actual_start_page,
                        last_page_seen=last_page_seen,
                        max_pages=max_pages,
                    )
                    if pbar.total != progress_total_pages:
                        pbar.total = progress_total_pages
                        pbar.refresh()

                validation = page_result["validation"]
                if validation.get("passed") or attempts >= PAGE_VALIDATION_RETRY_LIMIT:
                    break

                attempts += 1
                validation_retry_pages.append(page)
                logger.warning(
                    "Page %s validation failed, retrying with fresh HTML. Warnings: %s",
                    page,
                    "; ".join(validation.get("warnings", [])),
                )

            if page_result is None:
                logger.warning("No page result for page %s. Stopping.", page)
                break

            blocks = page_result["blocks_count"]
            if blocks == 0:
                logger.warning("No post blocks found on page %s. Stopping.", page)
                break

            validation = page_result["validation"]
            if not validation.get("passed"):
                validation_failures_this_run += 1
                if page not in validation_warning_pages:
                    validation_warning_pages.append(page)
                logger.warning("Page %s still failed validation: %s", page, "; ".join(validation.get("warnings", [])))

            page_posts = []
            page_images_downloaded = 0
            page_images_reused = 0

            for post in page_result["new_posts"]:
                image_paths = []
                for idx, img_url in enumerate(post["image_urls"], start=1):
                    stem = f"post_{post['post_id'] or post['post_number'] or page}_{idx:02d}"
                    rel_path, status = download_image(
                        session=session,
                        url=img_url,
                        folder=images_dir,
                        filename_stem=stem,
                        logger=logger,
                        download_cache=download_cache,
                    )
                    if rel_path:
                        image_paths.append(rel_path)
                    if status == "downloaded":
                        page_images_downloaded += 1
                    elif status == "reused":
                        page_images_reused += 1

                post["images"] = image_paths
                save_post_snapshot(post, posts_dir)
                page_posts.append(post)

                if post.get("post_id"):
                    seen_post_ids.add(post["post_id"])

            rejected_candidates_this_run += len(page_result["rejected_posts"])
            unknown_date_posts_this_run += validation.get("unknown_date_posts", 0)

            page_first_post_id = page_result["first_post_id"]
            if previous_first_post_id and page_first_post_id and page_first_post_id == previous_first_post_id:
                logger.warning("First post on page %s repeated from previous page; stopping to avoid looping.", page)
                break
            previous_first_post_id = page_first_post_id

            logger.info("New posts captured on page %s: %s", page, len(page_posts))
            all_posts = merge_posts(all_posts, page_posts)

            save_thread_json(all_posts, title=title, source_url=base_url, start_page=requested_start_page, out_path=thread_json_path)
            export_markdown(all_posts, title=title, source_url=base_url, out_path=thread_dir / "thread.md")
            export_html(all_posts, title=title, source_url=base_url, out_path=thread_dir / "thread.html")

            write_page_marker(
                thread_dir,
                page_num=page,
                page_url=page_url,
                title=title,
                new_posts_count=len(page_posts),
                new_images_downloaded=page_images_downloaded,
                new_images_reused=page_images_reused,
                used_cached_html=page_result["used_cached_html"],
                validation=validation,
                attempts=attempts + 1,
            )

            page_elapsed = time.time() - page_started_at
            page_durations.append(page_elapsed)
            if len(page_durations) > ROLLING_AVG_WINDOW:
                page_durations = page_durations[-ROLLING_AVG_WINDOW:]

            pages_completed_this_run += 1
            new_posts_saved_this_run += len(page_posts)
            images_downloaded_this_run += page_images_downloaded
            images_reused_this_run += page_images_reused
            last_completed_page_runtime = page

            average_seconds_per_page = choose_page_seconds_estimate(page_durations, historical_avg_seconds)
            next_page = page + 1

            if last_page_seen is not None and page >= last_page_seen:
                final_page_validation = validation
                final_page_verified, final_page_verification_reason = verify_final_page_completion(
                    last_page_seen=last_page_seen,
                    last_completed_page=page,
                    final_page_validation=validation,
                )
                finished_archive = final_page_verified

            write_resume_state(
                state_path,
                base_url=base_url,
                title=title,
                requested_start_page=requested_start_page,
                actual_start_page=actual_start_page,
                last_completed_page=page,
                next_page=next_page,
                last_page_seen=last_page_seen,
                finished=finished_archive,
                average_seconds_per_page=average_seconds_per_page,
                final_page_verified=final_page_verified,
                validation_warning_pages=validation_warning_pages,
                unknown_date_posts_total=unknown_date_posts_this_run,
                last_run_summary_path=summary_path,
            )

            pbar.update(1)
            completed_since_requested_start = completed_before_run + pages_completed_this_run
            progress_done = pages_completed_this_run if max_pages is not None else completed_since_requested_start
            full_remaining_pages = None
            if max_pages is not None and full_total_pages is not None:
                full_remaining_pages = max(0, full_total_pages - completed_since_requested_start)
            update_progress_display(
                pbar,
                session_elapsed_seconds=time.time() - started_at,
                pages_done_this_run=pages_completed_this_run,
                progress_done=progress_done,
                progress_total=progress_total_pages,
                page_durations=page_durations,
                historical_avg_seconds=historical_avg_seconds,
                full_remaining_pages=full_remaining_pages,
            )

            if last_page_seen is not None and page >= last_page_seen:
                logger.info("Reached detected last page (%s). Final verification: %s", last_page_seen, final_page_verification_reason)
                break

            if not page_posts and page > actual_start_page:
                logger.info("No new posts found on page %s; stopping.", page)
                break

            page = next_page
            time.sleep(REQUEST_DELAY_SECONDS)

    except KeyboardInterrupt:
        interrupted = True
        logger.warning("Interrupted by user. Resume will continue from the last fully committed page.")
    finally:
        pbar.close()

    next_page_for_resume = max(actual_start_page, last_completed_page_runtime + 1)
    average_seconds_per_page = choose_page_seconds_estimate(page_durations, historical_avg_seconds)

    if not final_page_validation and last_page_seen is not None and last_completed_page_runtime >= last_page_seen:
        final_page_verified, final_page_verification_reason = verify_final_page_completion(
            last_page_seen=last_page_seen,
            last_completed_page=last_completed_page_runtime,
            final_page_validation=final_page_validation,
        )

    write_resume_state(
        state_path,
        base_url=base_url,
        title=title or "Forex Factory Thread",
        requested_start_page=requested_start_page,
        actual_start_page=actual_start_page,
        last_completed_page=last_completed_page_runtime,
        next_page=next_page_for_resume,
        last_page_seen=last_page_seen,
        finished=finished_archive and not interrupted,
        average_seconds_per_page=average_seconds_per_page,
        final_page_verified=final_page_verified,
        validation_warning_pages=validation_warning_pages,
        unknown_date_posts_total=unknown_date_posts_this_run,
        last_run_summary_path=summary_path,
    )

    summary = build_run_summary(
        title=title or "Forex Factory Thread",
        base_url=base_url,
        thread_dir=thread_dir,
        requested_start_page=requested_start_page,
        actual_start_page=actual_start_page,
        last_completed_page_this_session=last_completed_page_runtime,
        next_page_for_resume=next_page_for_resume,
        last_page_seen=last_page_seen,
        finished_archive=finished_archive and not interrupted,
        interrupted=interrupted,
        resume_source=resume_source,
        max_pages_requested=max_pages,
        progress_total_pages=progress_total_pages,
        pages_completed_this_run=pages_completed_this_run,
        new_posts_saved_this_run=new_posts_saved_this_run,
        images_downloaded_this_run=images_downloaded_this_run,
        images_reused_this_run=images_reused_this_run,
        cached_html_pages_reused_this_run=cached_html_pages_reused_this_run,
        partial_files_cleaned_on_startup=partial_files_cleaned,
        total_posts_saved=len(all_posts),
        total_local_images=count_local_images(images_dir),
        average_seconds_per_page=average_seconds_per_page,
        validation_warning_pages=validation_warning_pages,
        validation_retry_pages=validation_retry_pages,
        validation_failures_this_run=validation_failures_this_run,
        rejected_candidates_this_run=rejected_candidates_this_run,
        unknown_date_posts_this_run=unknown_date_posts_this_run,
        final_page_verified=final_page_verified,
        final_page_verification_reason=final_page_verification_reason,
        final_page_validation=final_page_validation,
    )
    atomic_write_json(summary_path, summary)
    print_session_summary(summary, summary_path)
    print(f"Saved to: {thread_dir.resolve()}")
    return thread_dir



def resolve_thread_dir(base_url: str, output_root: Path) -> Path:
    base_url = normalize_thread_url(base_url)
    slug = slugify(base_url.rstrip("/").split("/")[-1])
    return output_root / slug


def resolve_archive_thread_dir(
    *,
    base_url: str | None = None,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    thread_dir: str | Path | None = None,
) -> Path:
    supplied = normalize_space(str(thread_dir or ""))
    if supplied:
        return Path(supplied).expanduser()
    if not normalize_space(str(base_url or "")):
        raise ValueError("Either --url or --thread-dir is required for archive mode.")
    return resolve_thread_dir(str(base_url), output_root)


def build_top10_summary(
    *,
    title: str,
    base_url: str,
    thread_dir: Path,
    total_posts: int,
    distinct_users: int,
    top_users: list[dict],
) -> dict:
    return {
        "mode": "top10",
        "thread_title": title,
        "thread_url": base_url,
        "output_folder": str(thread_dir.resolve()),
        "total_posts": total_posts,
        "distinct_users": distinct_users,
        "top_users": top_users,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def print_top10_summary(summary: dict, summary_path: Path) -> None:
    print("\nTop 10 Users (By Post)")
    print("-" * 60)
    print(f"Thread title: {summary.get('thread_title') or 'Unknown'}")
    print(f"Thread URL: {summary['thread_url']}")
    print(f"Output folder: {summary['output_folder']}")
    print(f"Total posts: {summary['total_posts']}")
    print(f"Distinct users: {summary['distinct_users']}")
    print("")
    for item in summary.get("top_users", []):
        print(
            f"User {item['rank']} = {item['author']} "
            f"({item['post_count']} posts, {item['share_percent']:.2f}%)"
        )
    print(f"\nSummary file: {summary_path.resolve()}")
    print("-" * 60)


def report_top10_users(
    *,
    base_url: str = "",
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    thread_dir: str | Path | None = None,
) -> Path:
    base_url = normalize_thread_url(base_url or "")
    thread_dir = resolve_archive_thread_dir(base_url=base_url, output_root=output_root, thread_dir=thread_dir)
    thread_json_path = thread_dir / "thread.json"
    summary_path = thread_dir / TOP10_REPORT_FILENAME

    if not thread_json_path.exists():
        raise FileNotFoundError(f"Could not find existing archive file: {thread_json_path}")

    archive_data = load_json_file(thread_json_path)
    posts = archive_data.get("posts", []) if isinstance(archive_data, dict) else []

    counts: dict[str, int] = {}
    for post in posts:
        author = normalize_space(str(post.get("author") or "Unknown")) or "Unknown"
        counts[author] = counts.get(author, 0) + 1

    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0].lower()))
    total_posts = len(posts)
    top_users = []
    for rank, (author, count) in enumerate(ranked[:10], start=1):
        share = (count / total_posts * 100.0) if total_posts else 0.0
        top_users.append(
            {
                "rank": rank,
                "author": author,
                "post_count": count,
                "share_percent": round(share, 2),
            }
        )

    summary = build_top10_summary(
        title=archive_data.get("title") or "Forex Factory Thread",
        base_url=str(archive_data.get("source_url") or base_url or ""),
        thread_dir=thread_dir,
        total_posts=total_posts,
        distinct_users=len(counts),
        top_users=top_users,
    )
    atomic_write_json(summary_path, summary)
    print_top10_summary(summary, summary_path)
    return thread_dir



def parse_users_filter(users_spec: str | None) -> list[str]:
    if not users_spec:
        return []
    seen: set[str] = set()
    users: list[str] = []
    for raw in str(users_spec).split(","):
        cleaned = normalize_space(raw)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        users.append(cleaned)
    return users


def sort_posts_for_export(posts: list[dict]) -> list[dict]:
    ordered = list(posts)

    def sort_key(post: dict) -> tuple:
        page = int(post.get("page") or 0)
        try:
            number = int(str(post.get("post_number") or "0").replace(",", ""))
        except Exception:
            number = 0
        return (page, number, str(post.get("post_id") or ""))

    ordered.sort(key=sort_key)
    return ordered


def filter_posts_by_users(posts: list[dict], users_spec: str | None) -> tuple[list[dict], list[str]]:
    selected_users = parse_users_filter(users_spec)
    if not selected_users:
        return sort_posts_for_export(posts), []

    allowed = {user.lower() for user in selected_users}
    filtered = [
        post for post in posts
        if normalize_space(str(post.get("author") or "")).lower() in allowed
    ]
    return sort_posts_for_export(filtered), selected_users


def filter_posts_by_pages(posts: list[dict], pages_spec: str | None) -> tuple[list[dict], list[int]]:
    selected_pages = parse_page_spec(pages_spec or "")
    if not selected_pages:
        return sort_posts_for_export(posts), []

    allowed = {int(page) for page in selected_pages}
    filtered = []
    for post in posts:
        try:
            page = int(post.get("page") or 0)
        except Exception:
            page = 0
        if page in allowed:
            filtered.append(post)
    return sort_posts_for_export(filtered), selected_pages


def collect_selected_posts(posts_spec: str | None, posts_file: str | None) -> list[int]:
    selected = set(parse_posts_spec(posts_spec or ""))
    for value in load_posts_spec_file(posts_file):
        selected.add(int(value))
    return sorted(value for value in selected if int(value) >= 1)


def filter_posts_by_post_numbers(
    posts: list[dict],
    posts_spec: str | None,
    posts_file: str | None,
) -> tuple[list[dict], list[int]]:
    selected_posts = collect_selected_posts(posts_spec, posts_file)
    if not selected_posts:
        return sort_posts_for_export(posts), []

    allowed = {int(number) for number in selected_posts}
    filtered = []
    for post in posts:
        try:
            number = int(str(post.get("post_number") or "0").replace(",", ""))
        except Exception:
            number = 0
        if number in allowed:
            filtered.append(post)
    return sort_posts_for_export(filtered), selected_posts


def apply_export_filters(
    posts: list[dict],
    users_spec: str | None,
    pages_spec: str | None,
    posts_spec: str | None,
    posts_file: str | None,
) -> tuple[list[dict], list[str], list[int], list[int]]:
    filtered_posts, selected_users = filter_posts_by_users(posts, users_spec)
    filtered_posts, selected_pages = filter_posts_by_pages(filtered_posts, pages_spec)
    filtered_posts, selected_posts = filter_posts_by_post_numbers(filtered_posts, posts_spec, posts_file)
    return sort_posts_for_export(filtered_posts), selected_users, selected_pages, selected_posts


def format_int_list(values: list[int], empty_label: str) -> str:
    if not values:
        return empty_label
    ordered = sorted({int(value) for value in values if int(value) >= 1})
    if not ordered:
        return empty_label

    chunks: list[str] = []
    start = ordered[0]
    end = ordered[0]
    for value in ordered[1:]:
        if value == end + 1:
            end = value
            continue
        chunks.append(str(start) if start == end else f"{start}-{end}")
        start = end = value
    chunks.append(str(start) if start == end else f"{start}-{end}")
    return ", ".join(chunks)


def format_page_list(pages: list[int]) -> str:
    return format_int_list(pages, "all pages")


def format_post_list(post_numbers: list[int]) -> str:
    return format_int_list(post_numbers, "all posts")


def build_export_filter_label(
    selected_users: list[str],
    selected_pages: list[int],
    selected_posts: list[int],
) -> str:
    labels: list[str] = []
    if selected_users:
        labels.append(", ".join(selected_users))
    else:
        labels.append("all posts")
    if selected_pages:
        labels.append(f"pages {format_page_list(selected_pages)}")
    if selected_posts:
        labels.append(f"posts {format_post_list(selected_posts)}")
    return " | ".join(labels)


def default_single_html_output_name(
    selected_users: list[str],
    selected_pages: list[int],
    selected_posts: list[int],
) -> str:
    parts: list[str] = []
    if selected_users:
        parts.append("_".join(slugify(user, max_len=24) for user in selected_users[:6]).strip("_") or "users")
    else:
        parts.append("all")
    if selected_pages:
        parts.append("pages_" + safe_filename(format_page_list(selected_pages), max_len=80))
    if selected_posts:
        parts.append(f"posts_{len(selected_posts)}")
    return f"single_export_{'_'.join(part for part in parts if part)}.html"


def build_single_html_export_summary(
    *,
    title: str,
    base_url: str,
    thread_dir: Path,
    output_file: Path,
    total_posts_in_archive: int,
    exported_posts: int,
    selected_users: list[str],
    selected_pages: list[int],
    selected_posts: list[int],
) -> dict:
    return {
        "mode": "single_html_export",
        "thread_title": title,
        "thread_url": base_url,
        "output_folder": str(thread_dir.resolve()),
        "output_file": str(output_file.resolve()),
        "total_posts_in_archive": total_posts_in_archive,
        "exported_posts": exported_posts,
        "selected_users": selected_users,
        "selected_pages": selected_pages,
        "selected_posts": selected_posts,
        "filter_label": build_export_filter_label(selected_users, selected_pages, selected_posts),
        "filter_mode": "all_posts" if (not selected_users and not selected_pages and not selected_posts) else "filtered",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def print_single_html_export_summary(summary: dict, summary_path: Path) -> None:
    print("\nSingle HTML Export")
    print("-" * 60)
    print(f"Thread title: {summary.get('thread_title') or 'Unknown'}")
    print(f"Thread URL: {summary['thread_url']}")
    print(f"Output folder: {summary['output_folder']}")
    print(f"Output file: {summary['output_file']}")
    print(f"Total posts in archive: {summary['total_posts_in_archive']}")
    print(f"Exported posts: {summary['exported_posts']}")
    print(f"Filter: {summary.get('filter_label') or 'all posts'}")
    print(f"\nSummary file: {summary_path.resolve()}")
    print("-" * 60)


def build_single_html_inline_css() -> str:
    return f"""body{{font-family:Arial,sans-serif;max-width:{EXPORT_CONTENT_MAX_WIDTH_PX}px;margin:2rem auto;padding:0 1.25rem;line-height:1.7;color:#e8e6e3;background:#151515}}
h1,h2,h3{{line-height:1.25;color:#f3efe9}}
a{{color:#9ecbff}}
a:visited{{color:#c8b0ff}}
.meta{{color:#b8b3ac;font-size:.98rem}}
.post{{border-top:1px solid #3a3a3a;padding:1.35rem 0}}
blockquote{{border-left:4px solid #7f6cff;margin:1rem 0;padding:.55rem 1rem;background:#1d1d22;color:#ece8ff}}
img{{max-width:100%;height:auto;display:block;margin:.9rem 0;border:1px solid #333;box-shadow:0 2px 10px rgba(0,0,0,.35)}}
.signature{{margin:1rem 0 0 0;padding-top:.85rem;border-top:1px solid #444;color:#d7d2cb}}
.attachments{{margin:1rem 0 0 0;padding:.35rem 0 .35rem 1rem;border-left:4px solid #888;background:#1c1c1c}}
.attachments p{{margin:.2rem 0}}
pre{{white-space:pre-wrap}}
code{{background:#262626;padding:.1rem .25rem;color:#f1eadb}}"""


def local_image_path_to_data_uri(thread_dir: Path, image_path: str) -> str:
    normalized = normalize_space(str(image_path or ""))
    if not normalized:
        return ""
    if normalized.lower().startswith(("data:", "http://", "https://")):
        return normalized

    candidate = (thread_dir / normalized).resolve()
    if not candidate.exists() or not candidate.is_file():
        return normalized

    mime_type, _ = mimetypes.guess_type(candidate.name)
    mime_type = mime_type or "application/octet-stream"
    payload = base64.b64encode(candidate.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{payload}"


def render_html_body_with_embedded_images(parts: list[str], body_text: str, images: list[str], thread_dir: Path) -> tuple[int, int]:
    image_index = 0
    paragraph_lines: list[str] = []
    quote_lines: list[str] = []
    embedded_count = 0
    fallback_count = 0

    def flush_buffers() -> None:
        flush_html_buffers(parts, paragraph_lines, quote_lines)

    for raw_line in body_text.splitlines():
        line = raw_line.rstrip()
        norm = normalize_space(line)

        if not norm:
            flush_buffers()
            continue

        if norm == POST_IMAGE_PLACEHOLDER:
            flush_buffers()
            if image_index < len(images):
                original_img = str(images[image_index])
                img_src = local_image_path_to_data_uri(thread_dir, original_img)
                if img_src and img_src.startswith("data:"):
                    embedded_count += 1
                else:
                    fallback_count += 1
                escaped_img = html.escape(img_src or original_img, quote=True)
                parts.append(
                    f"<img src='{escaped_img}' alt='post image' loading='lazy' "
                    f"style='width:min(100%, {EXPORT_IMAGE_DISPLAY_WIDTH_PX}px);height:auto;display:block;margin:.75rem 0;'>"
                )
                image_index += 1
            continue

        if line.startswith("> "):
            if paragraph_lines:
                flush_buffers()
            quote_lines.append(line[2:])
        else:
            if quote_lines:
                flush_buffers()
            paragraph_lines.append(line)

    flush_buffers()

    while image_index < len(images):
        original_img = str(images[image_index])
        img_src = local_image_path_to_data_uri(thread_dir, original_img)
        if img_src and img_src.startswith("data:"):
            embedded_count += 1
        else:
            fallback_count += 1
        escaped_img = html.escape(img_src or original_img, quote=True)
        parts.append(
            f"<img src='{escaped_img}' alt='post image' loading='lazy' "
            f"style='width:min(100%, {EXPORT_IMAGE_DISPLAY_WIDTH_PX}px);height:auto;display:block;margin:.75rem 0;'>"
        )
        image_index += 1

    return embedded_count, fallback_count


def export_single_html_from_archive(
    *,
    base_url: str = "",
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    thread_dir: str | Path | None = None,
    users_spec: str | None = None,
    pages_spec: str | None = None,
    posts_spec: str | None = None,
    posts_file: str | None = None,
    output_filename: str | None = None,
) -> Path:
    base_url = normalize_thread_url(base_url or "")
    thread_dir = resolve_archive_thread_dir(base_url=base_url, output_root=output_root, thread_dir=thread_dir)
    thread_json_path = thread_dir / "thread.json"
    summary_path = thread_dir / SINGLE_HTML_EXPORT_REPORT_FILENAME

    if not thread_json_path.exists():
        raise FileNotFoundError(f"Could not find existing archive file: {thread_json_path}")

    archive_data = load_json_file(thread_json_path)
    posts = archive_data.get("posts", []) if isinstance(archive_data, dict) else []
    filtered_posts, selected_users, selected_pages, selected_posts = apply_export_filters(
        posts,
        users_spec,
        pages_spec,
        posts_spec,
        posts_file,
    )

    output_name = normalize_space(output_filename or "")
    if output_name:
        output_name = safe_filename(output_name, max_len=180)
        if not output_name.lower().endswith(".html"):
            output_name += ".html"
    else:
        output_name = default_single_html_output_name(selected_users, selected_pages, selected_posts)

    output_file = thread_dir / output_name
    escaped_title = html.escape(str(archive_data.get("title") or "Forex Factory Thread"))
    thread_url = str(archive_data.get("source_url") or base_url or "")
    escaped_thread_url = html.escape(thread_url, quote=True)

    title_suffix = ""
    filter_label = build_export_filter_label(selected_users, selected_pages, selected_posts)
    if selected_users or selected_pages or selected_posts:
        title_suffix = " — " + filter_label

    parts = [
        "<!doctype html>",
        "<html><head><meta charset='utf-8'>",
        f"<title>{escaped_title}{html.escape(title_suffix)}</title>",
        "<style>",
        build_single_html_inline_css(),
        "</style>",
        "</head><body>",
        f"<h1>{escaped_title}</h1>",
        f"<p class='meta'><strong>Source:</strong> <a href='{escaped_thread_url}'>{html.escape(thread_url)}</a></p>",
        f"<p class='meta'><strong>Archived at:</strong> {datetime.now(timezone.utc).isoformat()}</p>",
        f"<p class='meta'><strong>Total posts in archive:</strong> {len(posts)}</p>",
        f"<p class='meta'><strong>Exported posts:</strong> {len(filtered_posts)}</p>",
    ]

    parts.append(f"<p class='meta'><strong>Filter:</strong> {html.escape(filter_label)}</p>")

    for idx, post in enumerate(filtered_posts, start=1):
        label = post.get("post_number") or idx
        post_url = html.escape(str(post.get("post_url") or ""), quote=True)
        author = html.escape(str(post.get("author") or "Unknown"))
        page = html.escape(str(post.get("page") or ""))
        timestamp = html.escape(str(post.get("timestamp") or "Unknown date"))
        permalink_text = html.escape(str(post.get("post_url") or ""))

        parts.append("<section class='post'>")
        parts.append(f"<h2>Post {html.escape(str(label))} — {author}</h2>")
        parts.append(f"<p class='meta'><strong>Page:</strong> {page}<br>")
        parts.append(f"<strong>Time:</strong> {timestamp}<br>")
        parts.append(f"<strong>Permalink:</strong> <a href='{post_url}'>{permalink_text}</a></p>")

        body_text, attachment_labels, signature_lines = export_sections(post)
        if body_text:
            render_html_body_with_images(parts, body_text, list(post.get("images") or []))

        if attachment_labels:
            parts.append("<div class='attachments'>")
            for attachment_label in attachment_labels:
                parts.append(f"<p><strong>Attachment:</strong> {html.escape(attachment_label)}</p>")
            parts.append("</div>")

        if signature_lines:
            parts.append("<div class='signature'>")
            for sig_line in signature_lines:
                parts.append(f"<p><strong>Sig:</strong> {html.escape(sig_line)}</p>")
            parts.append("</div>")

        parts.append("</section>")

    parts.append("</body></html>")
    atomic_write_text(output_file, "\n".join(parts), encoding="utf-8")

    summary = build_single_html_export_summary(
        title=str(archive_data.get("title") or "Forex Factory Thread"),
        base_url=thread_url,
        thread_dir=thread_dir,
        output_file=output_file,
        total_posts_in_archive=len(posts),
        exported_posts=len(filtered_posts),
        selected_users=selected_users,
        selected_pages=selected_pages,
        selected_posts=selected_posts,
    )
    atomic_write_json(summary_path, summary)
    print_single_html_export_summary(summary, summary_path)
    return output_file


def default_ai_html_output_name(
    selected_users: list[str],
    selected_pages: list[int],
    selected_posts: list[int],
) -> str:
    parts: list[str] = []
    if selected_users:
        parts.append("_".join(slugify(user, max_len=24) for user in selected_users[:6]).strip("_") or "users")
    else:
        parts.append("all")
    if selected_pages:
        parts.append("pages_" + safe_filename(format_page_list(selected_pages), max_len=80))
    if selected_posts:
        parts.append(f"posts_{len(selected_posts)}")
    return f"ai_export_{'_'.join(part for part in parts if part)}.html"


def build_ai_html_export_summary(
    *,
    title: str,
    base_url: str,
    thread_dir: Path,
    output_file: Path,
    total_posts_in_archive: int,
    exported_posts: int,
    selected_users: list[str],
    selected_pages: list[int],
    selected_posts: list[int],
    embedded_images: int,
    fallback_images: int,
) -> dict:
    return {
        "mode": "ai_html_export",
        "thread_title": title,
        "thread_url": base_url,
        "output_folder": str(thread_dir.resolve()),
        "output_file": str(output_file.resolve()),
        "total_posts_in_archive": total_posts_in_archive,
        "exported_posts": exported_posts,
        "selected_users": selected_users,
        "selected_pages": selected_pages,
        "selected_posts": selected_posts,
        "filter_label": build_export_filter_label(selected_users, selected_pages, selected_posts),
        "filter_mode": "all_posts" if (not selected_users and not selected_pages and not selected_posts) else "filtered",
        "embedded_images": embedded_images,
        "fallback_images": fallback_images,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def print_ai_html_export_summary(summary: dict, summary_path: Path) -> None:
    print("\nAI HTML Export")
    print("-" * 60)
    print(f"Thread title: {summary.get('thread_title') or 'Unknown'}")
    print(f"Thread URL: {summary['thread_url']}")
    print(f"Output folder: {summary['output_folder']}")
    print(f"Output file: {summary['output_file']}")
    print(f"Total posts in archive: {summary['total_posts_in_archive']}")
    print(f"Exported posts: {summary['exported_posts']}")
    print(f"Embedded images: {summary.get('embedded_images', 0)}")
    print(f"Fallback image refs: {summary.get('fallback_images', 0)}")
    print(f"Filter: {summary.get('filter_label') or 'all posts'}")
    print(f"\nSummary file: {summary_path.resolve()}")
    print("-" * 60)


def export_ai_html_from_archive(
    *,
    base_url: str = "",
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    thread_dir: str | Path | None = None,
    users_spec: str | None = None,
    pages_spec: str | None = None,
    posts_spec: str | None = None,
    posts_file: str | None = None,
    output_filename: str | None = None,
) -> Path:
    base_url = normalize_thread_url(base_url or "")
    thread_dir = resolve_archive_thread_dir(base_url=base_url, output_root=output_root, thread_dir=thread_dir)
    thread_json_path = thread_dir / "thread.json"
    summary_path = thread_dir / AI_HTML_EXPORT_REPORT_FILENAME

    if not thread_json_path.exists():
        raise FileNotFoundError(f"Could not find existing archive file: {thread_json_path}")

    archive_data = load_json_file(thread_json_path)
    posts = archive_data.get("posts", []) if isinstance(archive_data, dict) else []
    filtered_posts, selected_users, selected_pages, selected_posts = apply_export_filters(
        posts,
        users_spec,
        pages_spec,
        posts_spec,
        posts_file,
    )

    output_name = normalize_space(output_filename or "")
    if output_name:
        output_name = safe_filename(output_name, max_len=180)
        if not output_name.lower().endswith(".html"):
            output_name += ".html"
    else:
        output_name = default_ai_html_output_name(selected_users, selected_pages, selected_posts)

    output_file = thread_dir / output_name
    escaped_title = html.escape(str(archive_data.get("title") or "Forex Factory Thread"))
    thread_url = str(archive_data.get("source_url") or base_url or "")
    escaped_thread_url = html.escape(thread_url, quote=True)

    title_suffix = ""
    filter_label = build_export_filter_label(selected_users, selected_pages, selected_posts)
    if selected_users or selected_pages or selected_posts:
        title_suffix = " — " + filter_label

    parts = [
        "<!doctype html>",
        "<html><head><meta charset='utf-8'>",
        f"<title>{escaped_title}{html.escape(title_suffix)}</title>",
        "<style>",
        build_single_html_inline_css(),
        "</style>",
        "</head><body>",
        f"<h1>{escaped_title}</h1>",
        f"<p class='meta'><strong>Source:</strong> <a href='{escaped_thread_url}'>{html.escape(thread_url)}</a></p>",
        f"<p class='meta'><strong>Archived at:</strong> {datetime.now(timezone.utc).isoformat()}</p>",
        f"<p class='meta'><strong>Total posts in archive:</strong> {len(posts)}</p>",
        f"<p class='meta'><strong>Exported posts:</strong> {len(filtered_posts)}</p>",
    ]

    parts.append(f"<p class='meta'><strong>Filter:</strong> {html.escape(filter_label)}</p>")

    embedded_images = 0
    fallback_images = 0

    for idx, post in enumerate(filtered_posts, start=1):
        label = post.get("post_number") or idx
        post_url = html.escape(str(post.get("post_url") or ""), quote=True)
        author = html.escape(str(post.get("author") or "Unknown"))
        page = html.escape(str(post.get("page") or ""))
        timestamp = html.escape(str(post.get("timestamp") or "Unknown date"))
        permalink_text = html.escape(str(post.get("post_url") or ""))

        parts.append("<section class='post'>")
        parts.append(f"<h2>Post {html.escape(str(label))} — {author}</h2>")
        parts.append(f"<p class='meta'><strong>Page:</strong> {page}<br>")
        parts.append(f"<strong>Time:</strong> {timestamp}<br>")
        parts.append(f"<strong>Permalink:</strong> <a href='{post_url}'>{permalink_text}</a></p>")

        body_text, attachment_labels, signature_lines = export_sections(post)
        if body_text:
            embedded_here, fallback_here = render_html_body_with_embedded_images(
                parts,
                body_text,
                list(post.get("images") or []),
                thread_dir,
            )
            embedded_images += embedded_here
            fallback_images += fallback_here

        if attachment_labels:
            parts.append("<div class='attachments'>")
            for attachment_label in attachment_labels:
                parts.append(f"<p><strong>Attachment:</strong> {html.escape(attachment_label)}</p>")
            parts.append("</div>")

        if signature_lines:
            parts.append("<div class='signature'>")
            for sig_line in signature_lines:
                parts.append(f"<p><strong>Sig:</strong> {html.escape(sig_line)}</p>")
            parts.append("</div>")

        parts.append("</section>")

    parts.append("</body></html>")
    atomic_write_text(output_file, "\n".join(parts), encoding="utf-8")

    summary = build_ai_html_export_summary(
        title=str(archive_data.get("title") or "Forex Factory Thread"),
        base_url=thread_url,
        thread_dir=thread_dir,
        output_file=output_file,
        total_posts_in_archive=len(posts),
        exported_posts=len(filtered_posts),
        selected_users=selected_users,
        selected_pages=selected_pages,
        selected_posts=selected_posts,
        embedded_images=embedded_images,
        fallback_images=fallback_images,
    )
    atomic_write_json(summary_path, summary)
    print_ai_html_export_summary(summary, summary_path)
    return output_file


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Forex Factory thread archiver")
    parser.add_argument("--url", help="Full thread URL")
    parser.add_argument("--thread-dir", default=None, help="Direct path to an existing archived thread folder for offline modes")
    parser.add_argument("--start-page", type=int, default=None, help="Start page number")
    parser.add_argument("--username", default=None, help="Username/email if login is needed")
    parser.add_argument("--password", default=None, help="Password if login is needed")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT), help="Base output folder")
    parser.add_argument("--max-pages", type=int, default=None, help="Optional safety limit for testing")
    parser.add_argument("--force", action="store_true", help="Re-fetch cached raw HTML pages")
    parser.add_argument("--debug", action="store_true", help="Show detailed console logging")
    parser.add_argument("--no-resume", action="store_true", help="Ignore saved progress and start exactly from --start-page")
    parser.add_argument("--overlap-start-pages", type=int, default=DEFAULT_OVERLAP_START_PAGES, help="Optional overlap pages for deep starts on live threads")
    parser.add_argument("--repair-pages", default=None, help="Reprocess specific page(s) in an existing archive, e.g. 145 or 145,200-202")
    parser.add_argument("--repair-validation-warnings", action="store_true", help="Reprocess page(s) listed in the archive validation warnings")
    parser.add_argument("--top10", action="store_true", help="Report top 10 users by post count from an existing archive")
    parser.add_argument("--export-single-html", action="store_true", help="Export a dark-mode single HTML file from an existing archive")
    parser.add_argument("--users", default=None, help="Comma-separated usernames for offline single HTML export filtering")
    parser.add_argument("--single-html-output", default=None, help="Custom filename for the offline single HTML export")
    parser.add_argument("--export-ai-html", action="store_true", help="Export a dark-mode AI HTML file from an existing archive")
    parser.add_argument("--ai-html-output", default=None, help="Custom filename for the offline AI HTML export")
    parser.add_argument("--pages", default=None, help="Comma-separated page filter for offline exports, e.g. 145 or 145,200-202")
    parser.add_argument("--posts", default=None, help="Comma-separated thread post number filter for offline exports, e.g. 2886 or 2886,3000-3050")
    parser.add_argument("--posts-file", default=None, help="Text file containing thread post numbers / ranges for offline exports")
    return parser


def collect_inputs(args: argparse.Namespace) -> tuple[str, int, str, str]:
    offline_archive_mode = bool(args.top10 or args.export_single_html or args.export_ai_html)
    thread_dir_supplied = normalize_space(str(args.thread_dir or ""))

    url = (args.url or "").strip()
    if not url and not (offline_archive_mode and thread_dir_supplied):
        if offline_archive_mode:
            url = input("Paste the FULL thread URL (or use --thread-dir for offline mode):\n> ").strip()
        else:
            url = input("Paste the FULL thread URL:\n> ").strip()

    start_page = args.start_page
    if start_page is None:
        if args.repair_pages or args.repair_validation_warnings or args.top10 or args.export_single_html or args.export_ai_html:
            start_page = 1
        else:
            raw = input("Start from which page number? (default = 1) -> ").strip()
            start_page = int(raw) if raw.isdigit() and int(raw) >= 1 else 1

    username = args.username
    if username is None:
        if args.top10 or args.export_single_html or args.export_ai_html:
            username = ""
        else:
            username = input("Username/email (press Enter if not needed) -> ").strip()

    password = args.password
    if password is None:
        if args.top10 or args.export_single_html or args.export_ai_html:
            password = ""
        else:
            password = getpass.getpass("Password (press Enter if not needed) -> ")

    return url, start_page, username, password


if __name__ == "__main__":
    parser = build_arg_parser()
    args = parser.parse_args()

    clear_console()

    url, start_page, username, password = collect_inputs(args)
    output_root = Path(args.output_root)
    thread_dir_arg = normalize_space(str(args.thread_dir or "")) or None

    if args.top10:
        report_top10_users(
            base_url=url,
            output_root=output_root,
            thread_dir=thread_dir_arg,
        )
    elif args.export_single_html:
        export_single_html_from_archive(
            base_url=url,
            output_root=output_root,
            thread_dir=thread_dir_arg,
            users_spec=args.users,
            pages_spec=args.pages,
            posts_spec=args.posts,
            posts_file=args.posts_file,
            output_filename=args.single_html_output,
        )
    elif args.export_ai_html:
        export_ai_html_from_archive(
            base_url=url,
            output_root=output_root,
            thread_dir=thread_dir_arg,
            users_spec=args.users,
            pages_spec=args.pages,
            posts_spec=args.posts,
            posts_file=args.posts_file,
            output_filename=args.ai_html_output,
        )
    elif args.repair_pages or args.repair_validation_warnings:
        repair_archive_pages(
            base_url=url,
            start_page=start_page,
            username=username,
            password=password,
            output_root=output_root,
            force=True if not args.force else args.force,
            debug=args.debug,
            repair_pages_spec=args.repair_pages,
            repair_validation_warnings=args.repair_validation_warnings,
        )
    else:
        scrape_thread(
            base_url=url,
            start_page=start_page,
            username=username,
            password=password,
            output_root=output_root,
            max_pages=args.max_pages,
            force=args.force,
            debug=args.debug,
            resume_enabled=not args.no_resume,
            overlap_start_pages=max(0, int(args.overlap_start_pages or 0)),
        )
