from __future__ import annotations

from datetime import datetime, UTC
import html
import re

import pandas as pd

from ingestion.crossref import PaperRecord


def clean_text(text: str | None) -> str:
    """Clean HTML tags, unescape HTML entities, and normalize whitespace."""
    if not text:
        return ""
    # Unescape HTML entities (e.g., &amp; -> &, &lt; -> <)
    cleaned = html.unescape(str(text))
    # Strip HTML/XML tags (e.g. <jats:p>, <b>, etc.)
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    # Collapse multiple whitespaces/newlines into a single space
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def parse_date(date_str: str | None) -> str:
    """Parse and normalize date string to YYYY-MM-DD format."""
    if not date_str:
        return "1970-01-01"
    cleaned = str(date_str).strip()
    match = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", cleaned)
    if match:
        year, month, day = match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    match_year = re.search(r"\b(\d{4})\b", cleaned)
    if match_year:
        return f"{int(match_year.group(1)):04d}-01-01"
    return "1970-01-01"


def calculate_age_days(published_date_str: str, run_date: datetime) -> int:
    """Calculate the age in days from published date to run_date."""
    try:
        pub_dt = datetime.strptime(published_date_str, "%Y-%m-%d")
        run_dt = run_date.replace(tzinfo=None) if run_date.tzinfo else run_date
        diff = (run_dt - pub_dt).days
        return max(0, diff)
    except Exception:
        return 0


def format_author(a: str | dict | None) -> str:
    """Format single author entry, handling nested dicts or strings."""
    if not a:
        return ""
    if isinstance(a, dict):
        given = a.get("given", "").strip()
        family = a.get("family", "").strip()
        if given and family:
            return clean_text(f"{given} {family}")
        return clean_text(given or family or str(a))
    return clean_text(str(a))


def build_clean_dataframe(records: list[PaperRecord] | list[dict], run_date: datetime | None = None) -> pd.DataFrame:
    """Clean raw paper records into a structured pandas DataFrame ready for embedding and indexing.

    Returns a DataFrame containing the exact 10 fields required by the data contract:
    ['paper_id', 'title', 'summary', 'published', 'authors_joined',
     'categories_joined', 'age_days', 'text_for_embedding', 'abs_url', 'pdf_url']
    """
    if run_date is None:
        run_date = datetime.now(UTC)

    cleaned_rows = []

    for item in records:
        # Support both PaperRecord dataclass objects and raw dicts
        if isinstance(item, PaperRecord):
            paper_id = item.paper_id
            title_raw = item.title
            summary_raw = item.summary
            authors_raw = item.authors
            categories_raw = item.categories
            published_raw = item.published
            abs_url = item.abs_url
            pdf_url = item.pdf_url
        elif isinstance(item, dict):
            paper_id = item.get("paper_id", "")
            title_raw = item.get("title", "")
            summary_raw = item.get("summary", "")
            authors_raw = item.get("authors", [])
            categories_raw = item.get("categories", [])
            published_raw = item.get("published", "")
            abs_url = item.get("abs_url", "")
            pdf_url = item.get("pdf_url", "")
        else:
            continue

        if not paper_id:
            continue

        title = clean_text(title_raw)
        summary = clean_text(summary_raw)

        # Filter out invalid records: empty title or summary < 100 chars
        if not title or len(summary) < 100:
            continue

        # Format authors_joined
        if isinstance(authors_raw, list):
            authors_cleaned = [format_author(a) for a in authors_raw if a]
            authors_cleaned = [a for a in authors_cleaned if a]
            authors_joined = ", ".join(authors_cleaned)
        else:
            authors_joined = format_author(authors_raw)

        # Format categories_joined
        if isinstance(categories_raw, list):
            categories_cleaned = [clean_text(str(c)) for c in categories_raw if c]
            categories_cleaned = [c for c in categories_cleaned if c]
            categories_joined = ", ".join(categories_cleaned)
        else:
            categories_joined = clean_text(str(categories_raw))

        published = parse_date(published_raw)
        age_days = calculate_age_days(published, run_date)

        # Build standard text_for_embedding with explicit field prefixes
        text_for_embedding = f"Title: {title} | Authors: {authors_joined} | Summary: {summary}"

        cleaned_rows.append({
            "paper_id": str(paper_id).strip(),
            "title": title,
            "summary": summary,
            "published": published,
            "authors_joined": authors_joined,
            "categories_joined": categories_joined,
            "age_days": age_days,
            "text_for_embedding": text_for_embedding,
            "abs_url": str(abs_url or "").strip(),
            "pdf_url": str(pdf_url or "").strip(),
        })

    if not cleaned_rows:
        return pd.DataFrame(columns=[
            "paper_id", "title", "summary", "published", "authors_joined",
            "categories_joined", "age_days", "text_for_embedding", "abs_url", "pdf_url"
        ])

    df = pd.DataFrame(cleaned_rows)

    # Deduplicate by paper_id
    df = df.drop_duplicates(subset=["paper_id"], keep="first")

    # Sort by published date descending, then paper_id
    df = df.sort_values(by=["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)

    return df

