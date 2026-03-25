#!/usr/bin/env python3
from __future__ import annotations
"""
Daily Digest Generator

Fetches news from RSS feeds, creates engaging summaries using Gemini AI (free),
generates a beautiful web page, emails it to you, and uploads a PDF to Google Drive.

HOW TO CUSTOMISE:
  - Change news feeds, section prompts, or the Gemini model in the CONFIGURATION
    section below (marked with ===).
  - Everything above the first === line is boilerplate — you don't need to touch it.
"""

import os
import re
import io
import json
import datetime
import smtplib
import urllib.request
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import feedparser
from google import genai

# =============================================================================
# CONFIGURATION — this is the section to edit when you want to make changes
# =============================================================================

# Gemini model. "gemini-2.0-flash" is fast and completely free.
# Change to "gemini-2.0-pro-exp" for richer analysis (also free tier).
GEMINI_MODEL = "gemini-2.0-flash"

DIGEST_TITLE = "Daily Digest"

# Google Drive folder ID — taken from your folder URL.
# To use a different folder: open it in Drive, copy the last segment of the URL.
GOOGLE_DRIVE_FOLDER_ID = "1Jq_4eeYWuhpWUiwSNy9j28rkbCew657A"

# Your background — Gemini uses this to tailor the writing style and depth.
MY_BACKGROUND = """
Reader profile: senior data scientist working on the product side of a business,
with an electronics engineering degree. Loves physics, cutting-edge tech, and science.
Actively building strategy and business skills to move into a strategy role.
Enjoys science fiction and action/thrillers as genres. Also interested in health and fitness.
Writing style: intelligent, witty, engaging — never dry or academic.
Be direct. Use sharp analogies. Surface the "so what" clearly.
"""

# News sections. Add/remove RSS feeds, or change prompts to tune each section.
SECTIONS = {
    "data_ai": {
        "title": "Data & AI",
        "emoji": "📊",
        "accent": "#6c63ff",
        "feeds": [
            "https://towardsdatascience.com/feed",
            "https://www.kdnuggets.com/feed",
            "https://www.technologyreview.com/feed/",
        ],
        "prompt": (
            "Summarise the most important data science and AI developments today. "
            "Aimed at a senior product data scientist who knows the field well — "
            "skip the basics, focus on what is genuinely novel or consequential. "
            "What should a data scientist pay attention to right now?"
        ),
    },
    "tech": {
        "title": "Tech World",
        "emoji": "💻",
        "accent": "#43ffaf",
        "feeds": [
            "http://feeds.bbci.co.uk/news/technology/rss.xml",
            "https://feeds.arstechnica.com/arstechnica/index",
            "https://www.wired.com/feed/rss",
        ],
        "prompt": (
            "Summarise the biggest tech stories of the day. "
            "Cut through the noise — what actually matters and why? "
            "Connect stories to real-world consequences."
        ),
    },
    "finance": {
        "title": "Markets & Finance",
        "emoji": "📈",
        "accent": "#ffd166",
        "feeds": [
            "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
            "https://www.economist.com/finance-and-economics/rss.xml",
            "https://finance.yahoo.com/news/rssindex",
        ],
        "prompt": (
            "Summarise the global events and market-moving news today. "
            "For each major story, add a finance angle: how might this affect "
            "equities, bonds, currencies, or commodities? Think macro — "
            "what is the broader narrative the market is pricing in?"
        ),
    },
    "science": {
        "title": "Science",
        "emoji": "🔬",
        "accent": "#ff6584",
        "feeds": [
            "http://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
            "https://www.newscientist.com/feed/home/",
            "https://www.sciencedaily.com/rss/top/science.xml",
        ],
        "prompt": (
            "Summarise the most exciting science and technology breakthroughs. "
            "The reader has an electronics engineering background and loves physics — "
            "do not simplify unnecessarily. Make the wonder and scale of discoveries "
            "land. Prioritise physics, space, biology, and tech-adjacent science."
        ),
    },
    "strategy": {
        "title": "Strategy & Business",
        "emoji": "🎯",
        "accent": "#06d6a0",
        "feeds": [
            "https://feeds.hbr.org/harvardbusiness",
            "https://www.economist.com/business/rss.xml",
            "https://www.theguardian.com/business/rss",
        ],
        "prompt": (
            "Summarise key strategy and business insights from today. "
            "The reader is a data scientist actively growing into a strategy role — "
            "surface the frameworks, patterns, and strategic thinking in play. "
            "What is the strategic or business lesson from today's news?"
        ),
    },
}

# =============================================================================
# END OF CONFIGURATION — you do not need to edit below this line
# =============================================================================


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "")


def fetch_feed(url: str, max_items: int = 5) -> list[dict]:
    try:
        feed = feedparser.parse(url, request_headers={"User-Agent": "DailyDigest/1.0"})
        results = []
        for entry in feed.entries[:max_items]:
            title = entry.get("title", "").strip()
            summary = strip_html(
                entry.get("summary", entry.get("description", ""))
            )[:500].strip()
            if title:
                results.append({
                    "title": title,
                    "summary": summary,
                    "source": feed.feed.get("title", url),
                })
        return results
    except Exception as exc:
        print(f"  [warn] Could not fetch {url}: {exc}")
        return []


def fetch_section_articles(config: dict) -> list[dict]:
    articles = []
    seen_titles = set()
    for url in config["feeds"]:
        for article in fetch_feed(url):
            if article["title"] not in seen_titles:
                seen_titles.add(article["title"])
                articles.append(article)
    return articles[:12]


def fetch_random_concept() -> dict:
    try:
        req = urllib.request.Request(
            "https://en.wikipedia.org/api/rest_v1/page/random/summary",
            headers={"User-Agent": "DailyDigest/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
            return {
                "title": data.get("title", ""),
                "extract": data.get("extract", "")[:700],
                "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
            }
    except Exception as exc:
        print(f"  [warn] Random concept fetch failed: {exc}")
        return {
            "title": "Entropy",
            "extract": "In thermodynamics, entropy is a measure of disorder in a system.",
            "url": "https://en.wikipedia.org/wiki/Entropy",
        }


def markdown_to_html(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    return "".join(
        f"<p>{p.replace(chr(10), '<br>')}</p>" for p in paragraphs
    )


def gemini_summarise(client, section_title: str, articles: list[dict], prompt: str) -> str:
    if not articles:
        return "<p>No articles available today. Check back tomorrow.</p>"

    articles_text = "\n\n".join(
        f"[{a['source']}] {a['title']}\n{a['summary']}" for a in articles
    )
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=(
            f"{MY_BACKGROUND}\n\n"
            f"Section: {section_title}\n"
            f"Task: {prompt}\n\n"
            f"Today's articles:\n{articles_text}\n\n"
            "Write 3-4 engaging paragraphs (no bullet points, no sub-headers). "
            "End with a single bold sentence starting with **Key takeaway:**. "
            "Keep it under 380 words. Do not start with the word 'Today'."
        ),
    )
    return markdown_to_html(response.text)


def gemini_explain_concept(client, concept: dict) -> str:
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=(
            f"{MY_BACKGROUND}\n\n"
            f"Explain this concept engagingly in 2-3 paragraphs for someone "
            f"with a physics/engineering background:\n\n"
            f"Title: {concept['title']}\n"
            f"Wikipedia summary: {concept['extract']}\n\n"
            "Connect it to something interesting in the modern world if possible. "
            "End with one bold **surprising fact or implication**."
        ),
    )
    return markdown_to_html(response.text)


def build_web_html(sections: list[dict], concept: dict, date_str: str) -> str:
    nav_html = "".join(
        f'<a href="#{s["key"]}">{s["emoji"]} {s["title"]}</a>' for s in sections
    )
    nav_html += '<a href="#concept">🎲 Concept</a>'

    cards_html = ""
    for s in sections:
        sources_str = ", ".join(list(s["sources"])[:3])
        cards_html += f"""
        <div class="card" id="{s['key']}" style="--accent:{s['accent']}">
            <div class="card-header">
                <span class="emoji-icon">{s['emoji']}</span>
                <h2>{s['title']}</h2>
            </div>
            <div class="card-body">{s['content']}</div>
            <div class="card-footer">Sources: {sources_str}</div>
        </div>"""

    wiki_link = (
        f'<a href="{concept["url"]}" target="_blank">Read on Wikipedia &#8594;</a>'
        if concept.get("url") else ""
    )
    cards_html += f"""
        <div class="card concept-card" id="concept">
            <div class="card-header">
                <span class="emoji-icon">🎲</span>
                <h2>Today's Random Concept: {concept['title']}</h2>
            </div>
            <div class="card-body">{concept['content']}</div>
            <div class="card-footer">{wiki_link}</div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{DIGEST_TITLE} &mdash; {date_str}</title>
    <style>
        :root {{
            --bg: #0d1117;
            --surface: #161b22;
            --surface2: #21262d;
            --border: #30363d;
            --text: #e6edf3;
            --muted: #8b949e;
            --link: #58a6ff;
            --strong: #79c0ff;
            --radius: 10px;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.75;
        }}
        header {{
            background: var(--surface);
            border-bottom: 1px solid var(--border);
            padding: 2.5rem 1.5rem 2rem;
            text-align: center;
        }}
        header h1 {{
            font-size: 1.9rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            margin-bottom: 0.4rem;
        }}
        .date-line {{ color: var(--muted); font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.08em; }}
        .badge {{
            display: inline-block;
            margin-top: 0.8rem;
            background: var(--surface2);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 0.2rem 0.8rem;
            font-size: 0.75rem;
            color: var(--muted);
        }}
        nav {{
            background: var(--surface);
            border-bottom: 1px solid var(--border);
            padding: 0.6rem 1rem;
            overflow-x: auto;
            white-space: nowrap;
            text-align: center;
        }}
        nav a {{
            display: inline-block;
            color: var(--muted);
            text-decoration: none;
            padding: 0.3rem 0.7rem;
            border-radius: 20px;
            font-size: 0.8rem;
            margin: 0 0.1rem;
            transition: background 0.15s, color 0.15s;
        }}
        nav a:hover {{ background: var(--surface2); color: var(--text); }}
        .container {{ max-width: 760px; margin: 0 auto; padding: 1.75rem 1rem; }}
        .card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-left: 3px solid var(--accent, #6c63ff);
            border-radius: var(--radius);
            margin-bottom: 1.25rem;
            overflow: hidden;
        }}
        .card-header {{
            display: flex;
            align-items: center;
            gap: 0.7rem;
            padding: 1.2rem 1.5rem 1rem;
            border-bottom: 1px solid var(--border);
        }}
        .emoji-icon {{ font-size: 1.35rem; line-height: 1; }}
        .card-header h2 {{ font-size: 0.98rem; font-weight: 600; }}
        .card-body {{ padding: 1.2rem 1.5rem; color: #c9d1d9; font-size: 0.92rem; }}
        .card-body p {{ margin-bottom: 0.85rem; }}
        .card-body p:last-child {{ margin-bottom: 0; }}
        .card-body strong {{ color: var(--strong); font-weight: 600; }}
        .card-footer {{
            padding: 0.65rem 1.5rem;
            border-top: 1px solid var(--border);
            font-size: 0.74rem;
            color: var(--muted);
        }}
        .card-footer a {{ color: var(--link); text-decoration: none; }}
        .concept-card {{ border-left-color: #f78166; }}
        footer {{
            text-align: center;
            padding: 2rem 1rem;
            color: var(--muted);
            font-size: 0.77rem;
            border-top: 1px solid var(--border);
            margin-top: 1rem;
        }}
        @media (max-width: 600px) {{
            header h1 {{ font-size: 1.4rem; }}
            .card-header {{ padding: 1rem 1rem 0.75rem; }}
            .card-body {{ padding: 1rem; font-size: 0.9rem; }}
            .card-footer {{ padding: 0.6rem 1rem; }}
        }}
    </style>
</head>
<body>
    <header>
        <h1>&#128240; {DIGEST_TITLE}</h1>
        <div class="date-line">{date_str}</div>
        <div class="badge">&#9201; ~10&ndash;15 min read</div>
    </header>
    <nav>{nav_html}</nav>
    <div class="container">{cards_html}</div>
    <footer>
        Curated daily by Gemini AI &middot; BBC, The Economist, HBR, New Scientist, Wired &amp; more<br>
        {date_str}
    </footer>
</body>
</html>"""


def build_email_html(sections: list[dict], concept: dict, date_str: str) -> str:
    section_blocks = ""
    for s in sections:
        sources_str = ", ".join(list(s["sources"])[:3])
        section_blocks += f"""
        <div style="background:#ffffff;border:1px solid #d0d7de;border-left:4px solid {s['accent']};
                    border-radius:8px;padding:20px 24px;margin-bottom:20px;">
            <h2 style="font-size:15px;font-weight:700;color:#1f2328;margin:0 0 12px 0;">
                {s['emoji']} {s['title']}
            </h2>
            <div style="font-size:14px;color:#57606a;line-height:1.75;">
                {s['content']}
            </div>
            <p style="font-size:11px;color:#8c959f;margin:12px 0 0;
                      border-top:1px solid #f0f0f0;padding-top:8px;">
                Sources: {sources_str}
            </p>
        </div>"""

    wiki_link = (
        f'<a href="{concept["url"]}" style="color:#0969da;text-decoration:none;">Read on Wikipedia &#8594;</a>'
        if concept.get("url") else ""
    )
    section_blocks += f"""
        <div style="background:#fff8f6;border:1px solid #d0d7de;border-left:4px solid #f78166;
                    border-radius:8px;padding:20px 24px;margin-bottom:20px;">
            <h2 style="font-size:15px;font-weight:700;color:#1f2328;margin:0 0 12px 0;">
                🎲 Today's Random Concept: {concept['title']}
            </h2>
            <div style="font-size:14px;color:#57606a;line-height:1.75;">
                {concept['content']}
            </div>
            <p style="font-size:11px;color:#8c959f;margin:12px 0 0;
                      border-top:1px solid #f0f0f0;padding-top:8px;">
                {wiki_link}
            </p>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{DIGEST_TITLE} &mdash; {date_str}</title>
</head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
             background:#f6f8fa;margin:0;padding:24px 16px;">
    <div style="max-width:680px;margin:0 auto;">
        <div style="background:#24292f;border-radius:10px;padding:28px 24px;
                    text-align:center;margin-bottom:24px;">
            <h1 style="color:#ffffff;font-size:22px;font-weight:700;
                       letter-spacing:-0.02em;margin:0 0 6px;">
                &#128240; {DIGEST_TITLE}
            </h1>
            <p style="color:#8b949e;font-size:12px;margin:0;
                      text-transform:uppercase;letter-spacing:0.07em;">
                {date_str}
            </p>
        </div>
        {section_blocks}
        <p style="text-align:center;font-size:11px;color:#8c959f;padding:8px 0 16px;">
            Curated by Gemini AI &middot; {date_str}
        </p>
    </div>
</body>
</html>"""


def generate_pdf(html: str) -> bytes | None:
    try:
        from weasyprint import HTML
        return HTML(string=html).write_pdf()
    except Exception as exc:
        print(f"  [warn] PDF generation failed: {exc}")
        return None


def upload_to_drive(pdf_bytes: bytes, filename: str) -> str | None:
    """Upload PDF to the configured Google Drive folder."""
    service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not service_account_json:
        print("  [info] GOOGLE_SERVICE_ACCOUNT_JSON not set — skipping Drive upload.")
        return None

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseUpload

        creds = service_account.Credentials.from_service_account_info(
            json.loads(service_account_json),
            scopes=["https://www.googleapis.com/auth/drive.file"],
        )
        service = build("drive", "v3", credentials=creds, cache_discovery=False)

        file_metadata = {"name": filename, "parents": [GOOGLE_DRIVE_FOLDER_ID]}
        media = MediaIoBaseUpload(io.BytesIO(pdf_bytes), mimetype="application/pdf")
        uploaded = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id,webViewLink",
        ).execute()

        url = uploaded.get("webViewLink", "")
        print(f"  Uploaded to Google Drive: {url}")
        return url
    except Exception as exc:
        print(f"  [warn] Google Drive upload failed: {exc}")
        return None


def send_email(html: str, date_str: str, pdf_bytes: bytes | None = None) -> None:
    gmail_user = os.getenv("GMAIL_USER")
    gmail_app_password = os.getenv("GMAIL_APP_PASSWORD")
    email_to = os.getenv("EMAIL_TO")

    if not all([gmail_user, gmail_app_password, email_to]):
        print("  [info] Email env vars not configured — skipping email.")
        return

    msg = MIMEMultipart("mixed")
    msg["Subject"] = f"Daily Digest — {date_str}"
    msg["From"] = gmail_user
    msg["To"] = email_to

    body = MIMEMultipart("alternative")
    body.attach(MIMEText(html, "html"))
    msg.attach(body)

    if pdf_bytes:
        pdf_part = MIMEApplication(pdf_bytes, _subtype="pdf")
        filename = f"digest-{datetime.datetime.now().strftime('%Y-%m-%d')}.pdf"
        pdf_part.add_header("Content-Disposition", "attachment", filename=filename)
        msg.attach(pdf_part)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_app_password)
            server.sendmail(gmail_user, email_to, msg.as_string())
        print(f"  Email sent to {email_to}")
    except Exception as exc:
        print(f"  [warn] Email failed: {exc}")


def main() -> None:
    print(f"\n{'=' * 55}")
    print("  Daily Digest Generator")
    print(f"{'=' * 55}\n")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY environment variable is not set. "
            "Get a free key at aistudio.google.com and add it as a GitHub secret."
        )

    client = genai.Client(api_key=api_key)
    date_str = datetime.datetime.now().strftime("%A, %B %d, %Y")
    pdf_filename = f"digest-{datetime.datetime.now().strftime('%Y-%m-%d')}.pdf"

    sections_data = []
    for key, config in SECTIONS.items():
        print(f"Fetching {config['title']}...")
        articles = fetch_section_articles(config)
        print(f"  Got {len(articles)} articles. Summarising with Gemini...")
        content_html = gemini_summarise(client, config["title"], articles, config["prompt"])
        sections_data.append({
            "key": key,
            "title": config["title"],
            "emoji": config["emoji"],
            "accent": config["accent"],
            "content": content_html,
            "sources": list({a["source"] for a in articles[:4]}),
        })

    print("\nFetching random concept from Wikipedia...")
    concept_raw = fetch_random_concept()
    print(f"  Concept: {concept_raw['title']}. Explaining with Gemini...")
    concept_data = {
        "title": concept_raw["title"],
        "content": gemini_explain_concept(client, concept_raw),
        "url": concept_raw.get("url", ""),
    }

    print("\nBuilding HTML pages...")
    web_html = build_web_html(sections_data, concept_data, date_str)
    email_html = build_email_html(sections_data, concept_data, date_str)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(web_html)
    print("  Saved index.html")

    print("\nGenerating PDF...")
    pdf_bytes = generate_pdf(email_html)
    if pdf_bytes:
        print("  PDF ready.")
        print("\nUploading PDF to Google Drive...")
        upload_to_drive(pdf_bytes, pdf_filename)

    print("\nSending email...")
    send_email(email_html, date_str, pdf_bytes)

    print(f"\nDone! Digest for {date_str} is ready.\n")


if __name__ == "__main__":
    main()
