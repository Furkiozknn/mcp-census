# -*- coding: utf-8 -*-
"""One row per server: the latest-version set as a CSV or JSON Lines table.

`sayim.json` holds totals. Anyone who wants to ask a question the census does
not (which servers in a namespace are remote-only, which npm servers declare
no repository) needs the per-server facts those totals were computed from,
in a form a spreadsheet, `jq`, pandas or DuckDB can read. Re-deriving them
from 100k raw registry rows means re-implementing `analyze.py`; this module
exports exactly the fields `analyze.py` already uses, with the same
definitions, so a number in a spreadsheet and a number in `sayim.json` agree.

Deterministic: rows sorted by server name, columns in a fixed order, so two
exports of the same `kayitlar.jsonl` are byte-identical.

CSV cells that a spreadsheet would read as a formula (a leading `=`, `+`,
`-`, `@`, tab or carriage return) are prefixed with `'`. Registry fields
are written by anyone who publishes a server, and opening an export must not
run what they wrote. JSON Lines is left untouched: it is not evaluated.
"""
from __future__ import annotations

import csv
import io
import json
from collections import Counter
from typing import Any, Iterable

from . import analyze

COLUMNS = (
    "name",
    "namespace",
    "namespace_kind",
    "version",
    "status",
    "is_latest_flag",
    "version_count",
    "install_shape",
    "package_types",
    "remote_types",
    "repository_url",
    "repository_host",
    "description_chars",
)

_FORMULA_START = ("=", "+", "-", "@", "\t", "\r")


def rows(records: Iterable[dict]) -> list[dict[str, Any]]:
    """The latest-version set, one dict per server, sorted by name."""
    records = list(records)
    version_counts = Counter(analyze.ad(r) for r in records if analyze.ad(r))
    out: list[dict[str, Any]] = []
    for record in analyze.en_son_kayitlar(records):
        name = analyze.ad(record)
        url = analyze.depo_urlsi(record)
        host = url.split("//", 1)[-1].split("/", 1)[0].lower() if url else ""
        server = record.get("server") if isinstance(record.get("server"), dict) else {}
        out.append({
            "name": name,
            "namespace": analyze.namespace(record),
            "namespace_kind": analyze.namespace_kind(record),
            "version": analyze.surum(record),
            "status": analyze.durum(record),
            "is_latest_flag": analyze.en_son_mu(record),
            "version_count": version_counts[name],
            "install_shape": analyze.install_shape(record),
            "package_types": sorted({str(p.get("registryType") or "bilinmiyor")
                                     for p in analyze.paketler(record)}),
            "remote_types": sorted({str(r.get("type") or "bilinmiyor")
                                    for r in analyze.uzak_uclar(record)}),
            "repository_url": url or "",
            "repository_host": host,
            "description_chars": len(str(server.get("description") or "").strip()),
        })
    out.sort(key=lambda row: row["name"])
    return out


def _cell(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        value = ";".join(value)
    text = str(value)
    if text.startswith(_FORMULA_START):
        return "'" + text
    return text


def to_csv(table: list[dict[str, Any]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(COLUMNS)
    for row in table:
        writer.writerow([_cell(row[column]) for column in COLUMNS])
    return buffer.getvalue()


def to_jsonl(table: list[dict[str, Any]]) -> str:
    return "".join(
        json.dumps({c: row[c] for c in COLUMNS}, ensure_ascii=False) + "\n" for row in table
    )


FORMATS = {"csv": to_csv, "jsonl": to_jsonl}
