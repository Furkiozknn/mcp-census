# -*- coding: utf-8 -*-
"""Render the README chart (assets/okunacak-kod.svg) from a count.

The chart used to be drawn by hand. Every number on it is also in
`veri/sayim.json`, and a test checks that the two agree. The monthly `Sayim`
workflow rewrites `sayim.json` but cannot redraw a hand-made picture, so the
first monthly count (2026-10-01) left the chart, and with it the test, behind.

Generating the chart from the count removes the drift: the same `sayim.json`
always produces the same bytes, so the test can compare the file directly,
and redrawing after a new count is one command (`mcp-census gorsel`).

The layout reproduces the hand-drawn original exactly (a test feeds it the
16 September 2026 numbers and compares byte for byte). Bars are to scale:
640 px is every distinct server.
"""
from __future__ import annotations

from typing import Any

BAR_WIDTH = 640

_TR_MONTHS = (
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
)


class ChartError(ValueError):
    """The count lacks a value the chart needs."""


def _tr_int(n: int) -> str:
    """Turkish thousands separator: 32318 -> 32.318."""
    return f"{n:,}".replace(",", ".")


def _tr_pct(value: float) -> str:
    """One decimal, Turkish decimal comma: 23.0 -> 23,0."""
    return f"{value:.1f}".replace(".", ",")


def _aria_pct(value: float) -> str:
    """The screen-reader text drops a trailing ',0' (yuzde 23, yuzde 56,3)."""
    text = _tr_pct(value)
    return text[:-2] if text.endswith(",0") else text


def _tr_date(iso: str) -> str:
    """2026-09-16T04:08:56Z -> 16 Eylül 2026."""
    try:
        year, month, day = int(iso[0:4]), int(iso[5:7]), int(iso[8:10])
        return f"{day} {_TR_MONTHS[month - 1]} {year}"
    except (ValueError, IndexError):
        raise ChartError(f"indirme_zamani_utc is not an ISO date: {iso!r}") from None


def _values(count: dict[str, Any]) -> dict[str, Any]:
    findings = {b.get("ad"): b for b in (count.get("bulgular") or []) if isinstance(b, dict)}
    out: dict[str, Any] = {}
    for name in ("ayri_sunucu_adi", "deposuz_sunucu", "sadece_uzak_sunucu", "ne_paket_ne_uc"):
        finding = findings.get(name)
        if not finding or not isinstance(finding.get("deger"), int):
            raise ChartError(f"the count has no integer value for {name!r}")
        out[name] = finding["deger"]
        out[name + "_pct"] = finding.get("yuzde")
    total = out["ayri_sunucu_adi"]
    if total <= 0:
        raise ChartError("ayri_sunucu_adi must be positive")
    for name in ("deposuz_sunucu", "sadece_uzak_sunucu", "ne_paket_ne_uc"):
        if out[name + "_pct"] is None:
            out[name + "_pct"] = round(100.0 * out[name] / total, 1)
    hosts = (count.get("dagilimlar") or {}).get("depo_barindiricisi") or {}
    out["github"] = int(hosts.get("github.com", 0))
    out["gitlab"] = int(hosts.get("gitlab.com", 0))
    manifest = count.get("kaynak_manifest") or {}
    stamp = manifest.get("indirme_zamani_utc")
    if not stamp:
        raise ChartError("the count has no kaynak_manifest.indirme_zamani_utc")
    out["date"] = _tr_date(str(stamp))
    return out


_FONT_UI = "'Segoe UI', Verdana, sans-serif"


def _bar(y: int, label: str, value: int, pct: float, total: int, colour: str) -> str:
    width = round(BAR_WIDTH * value / total)
    number = _tr_int(value)
    # 10 px per character after the number, at least 50, as the hand-drawn
    # chart spaced it (7.439 -> +60, 18.183 -> +70, 425 -> +50).
    pct_x = 656 + max(50, 10 * len(number) + 10)
    return (
        f'    <g transform="translate(40,{y})">\n'
        f'      <text x="0" y="-8" font-family="{_FONT_UI}" font-size="13" fill="#c7c2b6">{label}</text>\n'
        f'      <rect x="0" y="0" width="{BAR_WIDTH}" height="20" rx="3" fill="#1c1c24"/>\n'
        f'      <rect x="0" y="0" width="{width}" height="20" rx="3" fill="{colour}"/>\n'
        f'      <text x="656" y="15" fill="{colour}">{number}</text>\n'
        f'      <text x="{pct_x}" y="15" fill="#6b6b77">%{_tr_pct(pct)}</text>\n'
        f'    </g>\n'
    )


def render(count: dict[str, Any]) -> str:
    """The whole SVG for one count, as text ending in a newline."""
    v = _values(count)
    total = v["ayri_sunucu_adi"]
    aria = (
        "Registry'nin dortte birinin okunacak kodu yok: "
        f"{_tr_int(total)} sunucunun {_tr_int(v['deposuz_sunucu'])}'unda repository alani hic yok "
        f"(yuzde {_aria_pct(v['deposuz_sunucu_pct'])}), "
        f"{_tr_int(v['sadece_uzak_sunucu'])}'u yalnizca uzak uc sunuyor "
        f"(yuzde {_aria_pct(v['sadece_uzak_sunucu_pct'])}), "
        f"{_tr_int(v['ne_paket_ne_uc'])}'i ne paket ne uzak uc bildiriyor "
        f"(yuzde {_aria_pct(v['ne_paket_ne_uc_pct'])}). "
        f"Kaynak kodu olanlarin {_tr_int(v['github'])}'i GitHub'da, {_tr_int(v['gitlab'])}'i GitLab'de."
    )
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 340" width="1000" height="340" '
        f'role="img" aria-label="{aria}">\n',
        "  <defs>\n",
        '    <linearGradient id="bg2" x1="0%" y1="0%" x2="100%" y2="100%">\n',
        '      <stop offset="0%" stop-color="#14141a"/>\n',
        '      <stop offset="100%" stop-color="#0b0b0f"/>\n',
        "    </linearGradient>\n",
        "  </defs>\n",
        '  <rect width="1000" height="340" rx="10" fill="url(#bg2)" stroke="#23232b"/>\n',
        "\n",
        f'  <text x="40" y="46" font-family="{_FONT_UI}" font-weight="600" font-size="17" '
        'fill="#e7dcc0">"Kurmadan önce kodu oku" tavsiyesi kaç kayıt için geçerli?</text>\n',
        f'  <text x="40" y="70" font-family="{_FONT_UI}" font-size="13" fill="#8d8d99">'
        f"{v['date']}, resmî registry'nin tamamı · {_tr_int(total)} ayrı sunucu</text>\n",
        "\n",
        f"  <!-- bars are drawn to scale: {BAR_WIDTH}px = {_tr_int(total)} servers -->\n",
        "  <g font-family=\"'Cascadia Code','Consolas',monospace\" font-size=\"13\">\n",
        _bar(104, "repository alanı hiç yok — statik denetleyicinin söyleyebileceği hiçbir şey yok",
             v["deposuz_sunucu"], v["deposuz_sunucu_pct"], total, "#f85149"),
        "\n",
        _bar(168, "yalnızca uzak uç — okuyabildiğiniz kod, çalışan kod olmak zorunda değil",
             v["sadece_uzak_sunucu"], v["sadece_uzak_sunucu_pct"], total, "#d29922"),
        "\n",
        _bar(232, "ne paket ne uzak uç — kurulacak bir şey yok",
             v["ne_paket_ne_uc"], v["ne_paket_ne_uc_pct"], total, "#8b949e"),
        "  </g>\n",
        "\n",
        '  <line x1="40" y1="280" x2="960" y2="280" stroke="#23232b"/>\n',
        f'  <text x="40" y="306" font-family="{_FONT_UI}" font-size="13" fill="#8d8d99">'
        "Kaynak kodu bildirenlerin neredeyse tamamı tek bir yerde: "
        f'<tspan fill="#6cb6ff">GitHub {_tr_int(v["github"])}</tspan> · '
        f'<tspan fill="#6b6b77">GitLab {_tr_int(v["gitlab"])}</tspan></text>\n',
        "</svg>\n",
    ]
    return "".join(parts)
