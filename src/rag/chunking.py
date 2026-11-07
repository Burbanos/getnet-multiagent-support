"""Text chunking module with boilerplate removal and size-capped chunk creation."""
from __future__ import annotations

from collections import Counter
from typing import Any


def _norm(line: str) -> str:
    """Normalize a line for boilerplate comparison."""
    return " ".join(line.split()).lower()


def _make_chunk(
    lines: list[str],
    idx: int,
    doc_sha256: str,
    doc_url: str,
    title: str,
    market: str,
    fetched_at: str,
) -> dict[str, Any]:
    """Assemble a chunk record dictionary."""
    return {
        "chunk_id": f"{doc_sha256[:12]}-{idx:03d}",
        "doc_url": doc_url,
        "title": title,
        "market": market,
        "fetched_at": fetched_at,
        "doc_sha256": doc_sha256,
        "text": "\n".join(lines),
    }


def build_chunks(
    records: list[dict[str, Any]],
    max_chars: int = 900,
    boilerplate_min_pages: int = 4,
    min_chars: int = 0,
) -> list[dict[str, Any]]:
    """
    Split clean 'ok' records into deterministic, verbatim text chunks.

    Filters boilerplate lines appearing in boilerplate_min_pages or more pages,
    empty lines, and lines without any alphanumeric character (e.g. '—').
    Groups remaining lines verbatim into chunks capped at max_chars characters.
    If min_chars > 0, pages with less than min_chars of retained text are dropped,
    and a trailing chunk smaller than min_chars is merged into the previous chunk.
    """
    ok_records = [r for r in records if r.get("status") == "ok"]

    # Identify boilerplate lines across distinct ok pages
    page_line_counts: Counter[str] = Counter()
    for rec in ok_records:
        text = rec.get("text") or ""
        page_norm_lines = {_norm(ln) for ln in text.split("\n") if _norm(ln)}
        page_line_counts.update(page_norm_lines)

    boilerplate = {
        nline for nline, count in page_line_counts.items() if count >= boilerplate_min_pages
    }

    chunks: list[dict[str, Any]] = []

    for rec in ok_records:
        text = rec.get("text") or ""
        doc_url = rec.get("url") or rec.get("doc_url") or ""
        doc_sha256 = rec.get("sha256") or rec.get("doc_sha256") or ""
        title = rec.get("title") or ""
        market = rec.get("market") or ""
        fetched_at = rec.get("fetched_at") or ""

        # Filter lines
        filtered_lines: list[str] = []
        for line in text.split("\n"):
            nline = _norm(line)
            if not nline:
                continue
            if not any(ch.isalnum() for ch in line):
                continue
            if nline in boilerplate:
                continue
            filtered_lines.append(line)

        # Check min_chars requirement for the whole page
        page_text_len = sum(len(line) for line in filtered_lines) + max(0, len(filtered_lines) - 1)
        if min_chars > 0 and page_text_len < min_chars:
            continue

        # Pack lines into chunks of up to max_chars characters
        page_chunks: list[dict[str, Any]] = []
        chunk_idx = 0
        current_lines: list[str] = []
        current_len = 0

        for raw_line in filtered_lines:
            line = raw_line[:max_chars] if len(raw_line) > max_chars else raw_line
            line_len = len(line)

            if not current_lines:
                current_lines.append(line)
                current_len = line_len
            else:
                new_len = current_len + 1 + line_len
                if new_len <= max_chars:
                    current_lines.append(line)
                    current_len = new_len
                else:
                    page_chunks.append(
                        _make_chunk(
                            current_lines,
                            chunk_idx,
                            doc_sha256,
                            doc_url,
                            title,
                            market,
                            fetched_at,
                        )
                    )
                    chunk_idx += 1
                    current_lines = [line]
                    current_len = line_len

        if current_lines:
            page_chunks.append(
                _make_chunk(
                    current_lines,
                    chunk_idx,
                    doc_sha256,
                    doc_url,
                    title,
                    market,
                    fetched_at,
                )
            )

        # Merge trailing chunk shorter than min_chars into the previous chunk of the same page
        if min_chars > 0 and len(page_chunks) > 1 and len(page_chunks[-1]["text"]) < min_chars:
            short_tail = page_chunks.pop()
            prev_chunk = page_chunks[-1]
            prev_chunk["text"] = prev_chunk["text"] + "\n" + short_tail["text"]

        chunks.extend(page_chunks)

    return chunks
