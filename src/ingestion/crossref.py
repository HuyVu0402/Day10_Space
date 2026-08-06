from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.config import Settings
from datetime import UTC, datetime
import hashlib
import json
import logging
import re
import time
from dataclasses import asdict
from typing import Any, List

import requests


# --- Raw snapshot / lineage contract (owned by R2 - Source Ingestion) -------
# data/raw/crossref_response.json is stored as a lineage envelope:
#   {"schema_version", "artifact", "lineage": {...}, "payload": <raw Crossref JSON>}
# The untouched HTTP payload stays under "payload" so the snapshot remains
# auditable and replayable offline, while "lineage" records where/when/how it
# was fetched and a checksum that proves the payload was not edited later.
RAW_RESPONSE_SCHEMA_VERSION = "1.0"
RAW_RESPONSE_ARTIFACT = "crossref_raw_response"
INGESTION_VERSION = "1.0.0"
CROSSREF_WORKS_URL = "https://api.crossref.org/works"
REQUEST_TIMEOUT_SECONDS = 15
REQUEST_MAX_RETRIES = 5
USER_AGENT = "day10-data-pipeline/1.0 (mailto:student@example.org)"
PAPER_ID_STRATEGY = "lowercased Crossref DOI"
RAW_RECORDS_ARTIFACT_PATH = "data/raw/crossref_records.json"


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


def payload_checksum(payload: dict) -> str:
    """Stable sha256 of the raw payload, used as the snapshot integrity seal."""
    canonical = json.dumps(payload or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def is_lineage_envelope(document: Any) -> bool:
    return (
        isinstance(document, dict)
        and isinstance(document.get("lineage"), dict)
        and isinstance(document.get("payload"), dict)
    )


def unwrap_raw_response(document: Any) -> dict:
    """Return the Crossref payload from a lineage envelope or a bare payload."""
    if is_lineage_envelope(document):
        return document["payload"]
    return document if isinstance(document, dict) else {}


def read_lineage(document: Any) -> dict:
    """Return the lineage block of an envelope, or {} for a legacy bare payload."""
    return document["lineage"] if is_lineage_envelope(document) else {}


def build_lineage_envelope(
    payload: dict,
    *,
    settings: Settings,
    params: dict,
    http_status: int,
    attempts: int,
    fetched_at: str,
    records_parsed: int,
) -> dict:
    """Wrap a raw Crossref payload with the source lineage required by R1/R3."""
    message = payload.get("message", {}) if isinstance(payload, dict) else {}
    items = message.get("items", []) if isinstance(message, dict) else []

    return {
        "schema_version": RAW_RESPONSE_SCHEMA_VERSION,
        "artifact": RAW_RESPONSE_ARTIFACT,
        "lineage": {
            "owner_role": "R2 - Source Ingestion Owner",
            "source_api": settings.source_api,
            "fetched_at": fetched_at,
            "fetched_by": "src/ingestion/crossref.py::fetch_source_records",
            "ingestion_version": INGESTION_VERSION,
            "request": {
                "method": "GET",
                "url": CROSSREF_WORKS_URL,
                "params": dict(params),
                "user_agent": USER_AGENT,
                "timeout_seconds": REQUEST_TIMEOUT_SECONDS,
                "max_retries": REQUEST_MAX_RETRIES,
            },
            "response": {
                "http_status": http_status,
                "attempts": attempts,
                "items_returned": len(items) if isinstance(items, list) else 0,
                "items_per_page": message.get("items-per-page") if isinstance(message, dict) else None,
                "total_results": message.get("total-results") if isinstance(message, dict) else None,
                "message_type": payload.get("message-type") if isinstance(payload, dict) else None,
                "message_version": payload.get("message-version") if isinstance(payload, dict) else None,
            },
            "parsing": {
                "records_parsed": records_parsed,
                "records_artifact": RAW_RECORDS_ARTIFACT_PATH,
                "paper_id_strategy": PAPER_ID_STRATEGY,
                "required_fields": ["DOI", "title", "abstract|description"],
            },
            "integrity": {
                "checksum_algorithm": "sha256",
                "payload_sha256": payload_checksum(payload),
            },
        },
        "payload": payload,
    }


def write_raw_response(
    path: Path,
    payload: dict,
    *,
    settings: Settings,
    params: dict,
    http_status: int,
    attempts: int,
    fetched_at: str,
    records_parsed: int,
) -> dict:
    """Persist the raw payload as a lineage envelope and return that envelope."""
    envelope = build_lineage_envelope(
        payload,
        settings=settings,
        params=params,
        http_status=http_status,
        attempts=attempts,
        fetched_at=fetched_at,
        records_parsed=records_parsed,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(envelope, fh, ensure_ascii=False, indent=2)
    return envelope


def load_raw_response(path: Path) -> tuple[dict, dict]:
    """Read the raw snapshot and return (payload, lineage) for offline replay."""
    if not path.exists():
        raise FileNotFoundError(f"Raw response snapshot not found: {path}")

    with open(path, "r", encoding="utf-8") as fh:
        document = json.load(fh)

    return unwrap_raw_response(document), read_lineage(document)


def verify_raw_response(path: Path) -> dict:
    """Audit the raw snapshot: envelope shape, checksum and item/record counts."""
    payload, lineage = load_raw_response(path)
    expected = (lineage.get("integrity") or {}).get("payload_sha256")
    actual = payload_checksum(payload)
    items = payload.get("message", {}).get("items", []) if isinstance(payload, dict) else []
    records = parse_crossref_payload(payload)
    ids = [r.paper_id for r in records]

    return {
        "path": str(path),
        "has_lineage_envelope": bool(lineage),
        "schema_version": RAW_RESPONSE_SCHEMA_VERSION if lineage else None,
        "fetched_at": lineage.get("fetched_at"),
        "source_api": lineage.get("source_api"),
        "http_status": (lineage.get("response") or {}).get("http_status"),
        "items_in_payload": len(items) if isinstance(items, list) else 0,
        "records_parsed": len(records),
        "records_declared": (lineage.get("parsing") or {}).get("records_parsed"),
        "duplicate_paper_ids": len(ids) - len(set(ids)),
        "checksum_expected": expected,
        "checksum_actual": actual,
        "checksum_ok": bool(expected) and expected == actual,
    }


def raw_snapshot_fingerprint(settings: Settings) -> dict:
    """File-level sha256 of both raw artifacts.

    Corruption must never touch data/raw/, so R1/R3 can take this fingerprint
    before and after the corruption flow and compare the two dicts.
    """
    fingerprint: dict[str, str | None] = {}
    for name, path in (
        ("crossref_response.json", settings.paths.raw_api_response),
        ("crossref_records.json", settings.paths.raw_records_json),
    ):
        if not path.exists():
            fingerprint[name] = None
            continue
        fingerprint[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return fingerprint


def assert_raw_snapshot_intact(settings: Settings) -> dict:
    """Fail loudly when the raw snapshot was edited after ingestion."""
    report = verify_raw_response(settings.paths.raw_api_response)
    if not report["has_lineage_envelope"]:
        raise RuntimeError(
            f"Raw snapshot {settings.paths.raw_api_response} has no lineage envelope; re-fetch with fetch_source_records()."
        )
    if not report["checksum_ok"]:
        raise RuntimeError(
            "Raw snapshot payload does not match its recorded sha256; data/raw/ was modified after ingestion."
        )
    return report


def rebuild_records_from_snapshot(path: Path) -> list[PaperRecord]:
    """Re-derive PaperRecords from the saved response — offline, no API call.

    Repair (R3) uses data/raw/crossref_records.json directly; this is the
    fallback that regenerates that file from the sealed HTTP payload.
    """
    payload, _ = load_raw_response(path)
    return parse_crossref_payload(payload)


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    payload = unwrap_raw_response(payload)
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
    url = CROSSREF_WORKS_URL
    params = {
        "query.bibliographic": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }

    headers = {"User-Agent": USER_AGENT}

    max_retries = REQUEST_MAX_RETRIES
    backoff = 1.0
    last_err = None

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
            if resp.status_code == 200:
                payload = resp.json()
                records = parse_crossref_payload(payload)

                # Store the untouched payload inside a lineage envelope so the
                # snapshot stays auditable and repair can replay it offline.
                write_raw_response(
                    settings.paths.raw_api_response,
                    payload,
                    settings=settings,
                    params=params,
                    http_status=resp.status_code,
                    attempts=attempt,
                    fetched_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    records_parsed=len(records),
                )

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
