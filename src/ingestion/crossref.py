from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.config import Settings
import json
import logging
import re
import time
from dataclasses import asdict
from typing import List

import requests


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """TODO(student): parse Crossref payload thanh list PaperRecord.

    Pseudo-code:
    1. Duyet `payload["message"]["items"]`.
    2. Lay DOI, title, abstract, authors, subject, dates, URLs.
    3. Chuan hoa text va bo record khong hop le.
    4. Tra ve list `PaperRecord`.
    """
    items = payload.get("message", {}).get("items", []) if isinstance(payload, dict) else []
    records: List[PaperRecord] = []

    for item in items:
        doi = item.get("DOI")
        if not doi:
            # require stable identifier
            continue
        paper_id = str(doi).lower().strip()

        # title may be list
        title_list = item.get("title") or []
        title = " ".join([t.strip() for t in title_list if isinstance(t, str)]) if title_list else ""

        # abstract may come under 'abstract' (string) or 'description' (list)
        summary = item.get("abstract") or ""
        if not summary:
            desc = item.get("description") or []
            if isinstance(desc, list):
                summary = " ".join([d.strip() for d in desc if isinstance(d, str)])
            elif isinstance(desc, str):
                summary = desc.strip()

        # minimal filter: need title and summary
        if not title or not summary:
            continue

        # authors
        authors = []
        for a in item.get("author", []) or []:
            if not isinstance(a, dict):
                continue
            given = a.get("given") or ""
            family = a.get("family") or ""
            name = (given + " " + family).strip() if (given or family) else a.get("name") or ""
            if name:
                authors.append(name)

        # subjects
        subjects = item.get("subject") or []
        categories = [s for s in subjects if isinstance(s, str)]
        primary_category = categories[0] if categories else ""

        # dates: try common Crossref fields
        def _date_from_parts(obj):
            if not isinstance(obj, dict):
                return ""
            # prefer date-time if present
            dt = obj.get("date-time")
            if dt:
                return dt
            parts = obj.get("date-parts") or []
            if parts and isinstance(parts, list) and parts[0]:
                try:
                    return "-".join(str(x) for x in parts[0])
                except Exception:
                    return ""
            return ""

        published = _date_from_parts(item.get("issued") or item.get("published-print") or item.get("created"))
        updated = _date_from_parts(item.get("deposited") or item.get("updated") or item.get("issued"))

        abs_url = item.get("URL") or ""

        # find pdf link if any
        pdf_url = ""
        for link in item.get("link", []) or []:
            if not isinstance(link, dict):
                continue
            content_type = (link.get("content-type") or "").lower()
            url = link.get("URL") or link.get("url") or link.get("URL")
            if "pdf" in content_type or (isinstance(url, str) and url.lower().endswith(".pdf")):
                pdf_url = url
                break

        # comment / container
        container = item.get("container-title") or []
        comment = " ".join([c for c in container if isinstance(c, str)]) if container else item.get("short-container-title") or ""

        # basic normalization: strip whitespace and collapse multiple spaces
        def _norm(s: str) -> str:
            if not isinstance(s, str):
                return ""
            s = s.strip()
            s = re.sub(r"\s+", " ", s)
            return s

        record = PaperRecord(
            paper_id=_norm(paper_id),
            title=_norm(title),
            summary=_norm(summary),
            authors=[_norm(a) for a in authors],
            categories=[_norm(c) for c in categories],
            primary_category=_norm(primary_category),
            published=_norm(published),
            updated=_norm(updated),
            abs_url=_norm(abs_url),
            pdf_url=_norm(pdf_url),
            comment=_norm(comment),
        )

        records.append(record)

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """TODO(student): goi source API, luu raw response, parse thanh records.

    Pseudo-code:
    1. Tao params tu `settings.source_query`, `settings.source_filter`, `settings.max_results`.
    2. Goi API voi retry cho cac status code nhu 429/503.
    3. Luu raw response vao `settings.paths.raw_api_response`.
    4. Parse payload bang `parse_crossref_payload`.
    5. Luu records vao `settings.paths.raw_records_json`.
    """
    url = "https://api.crossref.org/works"
    params = {
        "query.bibliographic": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }

    headers = {"User-Agent": "day10-data-pipeline/1.0 (mailto:student@example.org)"}

    max_retries = 5
    backoff = 1.0
    last_err = None

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            if resp.status_code == 200:
                payload = resp.json()
                # ensure parent dir exists
                settings.paths.raw_api_response.parent.mkdir(parents=True, exist_ok=True)
                with open(settings.paths.raw_api_response, "w", encoding="utf-8") as fh:
                    json.dump(payload, fh, ensure_ascii=False, indent=2)

                records = parse_crossref_payload(payload)

                # save flattened records
                settings.paths.raw_records_json.parent.mkdir(parents=True, exist_ok=True)
                with open(settings.paths.raw_records_json, "w", encoding="utf-8") as fh:
                    json.dump([asdict(r) for r in records], fh, ensure_ascii=False, indent=2)

                return records

            # retryable status codes
            if resp.status_code in {429, 500, 502, 503, 504}:
                last_err = RuntimeError(f"Retryable status {resp.status_code}")
                time.sleep(backoff)
                backoff *= 2
                continue

            # other non-success codes -> raise
            resp.raise_for_status()

        except Exception as exc:
            last_err = exc
            # on network related errors, backoff and retry
            time.sleep(backoff)
            backoff *= 2
            continue

    logging.error("Failed to fetch Crossref after %s attempts: %s", max_retries, last_err)
    raise last_err if last_err is not None else RuntimeError("Failed to fetch Crossref")


def load_raw_records(path: Path) -> list[PaperRecord]:
    """TODO(student): doc JSON snapshot va map thanh `PaperRecord`."""
    if not path.exists():
        raise FileNotFoundError(f"Raw records file not found: {path}")

    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    records: List[PaperRecord] = []
    for item in data or []:
        if not isinstance(item, dict):
            continue
        try:
            pr = PaperRecord(
                paper_id=item.get("paper_id", ""),
                title=item.get("title", ""),
                summary=item.get("summary", ""),
                authors=item.get("authors", []) or [],
                categories=item.get("categories", []) or [],
                primary_category=item.get("primary_category", ""),
                published=item.get("published", ""),
                updated=item.get("updated", ""),
                abs_url=item.get("abs_url", ""),
                pdf_url=item.get("pdf_url", ""),
                comment=item.get("comment", ""),
            )
            records.append(pr)
        except Exception:
            # skip malformed entries
            continue

    return records
