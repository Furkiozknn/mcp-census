# -*- coding: utf-8 -*-
"""The README chart is generated from the count, so it cannot drift from it."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from mcp_census import cli, gorsel

KOK = Path(__file__).resolve().parent.parent

# The numbers the hand-drawn chart showed (16 September 2026).
ESKI = {
    "bulgular": [
        {"ad": "ayri_sunucu_adi", "deger": 32318, "yuzde": 30.8, "tanim": "t"},
        {"ad": "deposuz_sunucu", "deger": 7439, "yuzde": 23.0, "tanim": "t"},
        {"ad": "sadece_uzak_sunucu", "deger": 18183, "yuzde": 56.3, "tanim": "t"},
        {"ad": "ne_paket_ne_uc", "deger": 425, "yuzde": 1.3, "tanim": "t"},
    ],
    "dagilimlar": {"depo_barindiricisi": {"github.com": 24841, "gitlab.com": 38}},
    "kaynak_manifest": {"indirme_zamani_utc": "2026-09-16T04:08:56Z"},
}


def test_committed_chart_is_exactly_what_the_count_renders():
    sayim = json.loads((KOK / "veri" / "sayim.json").read_text(encoding="utf-8"))
    svg = (KOK / "assets" / "okunacak-kod.svg").read_text(encoding="utf-8")
    assert gorsel.render(sayim) == svg, "run `mcp-census gorsel` after a new count"


def test_layout_matches_the_hand_drawn_original():
    svg = gorsel.render(ESKI)
    assert "16 Eylül 2026, resmî registry'nin tamamı · 32.318 ayrı sunucu" in svg
    assert '<rect x="0" y="0" width="147" height="20" rx="3" fill="#f85149"/>' in svg
    assert '<rect x="0" y="0" width="360" height="20" rx="3" fill="#d29922"/>' in svg
    assert '<rect x="0" y="0" width="8" height="20" rx="3" fill="#8b949e"/>' in svg
    # percentage label positions of the original: +60, +70, +50
    assert '<text x="716" y="15" fill="#6b6b77">%23,0</text>' in svg
    assert '<text x="726" y="15" fill="#6b6b77">%56,3</text>' in svg
    assert '<text x="706" y="15" fill="#6b6b77">%1,3</text>' in svg
    assert "(yuzde 23)" in svg and "(yuzde 56,3)" in svg
    assert "GitHub 24.841</tspan>" in svg and "GitLab 38</tspan>" in svg


def test_bars_are_to_scale():
    svg = gorsel.render(ESKI)
    widths = [int(w) for w in re.findall(
        r'<rect x="0" y="0" width="(\d+)" height="20" rx="3" fill="#(?!1c1c24)', svg)]
    for width, value in zip(widths, (7439, 18183, 425)):
        assert abs(width - 640 * value / 32318) < 1.0


def test_rendering_is_deterministic():
    assert gorsel.render(ESKI) == gorsel.render(json.loads(json.dumps(ESKI)))


def test_missing_percentage_is_computed():
    sayim = json.loads(json.dumps(ESKI))
    sayim["bulgular"][1]["yuzde"] = None
    assert "%23,0" in gorsel.render(sayim)


@pytest.mark.parametrize("bozuk,ileti", [
    ({"bulgular": []}, "ayri_sunucu_adi"),
    ({**ESKI, "kaynak_manifest": {}}, "indirme_zamani_utc"),
    ({**ESKI, "kaynak_manifest": {"indirme_zamani_utc": "dun"}}, "ISO"),
])
def test_incomplete_count_is_a_clear_error(bozuk, ileti):
    with pytest.raises(gorsel.ChartError, match=ileti):
        gorsel.render(bozuk)


def test_month_names_are_turkish():
    for ay, ad in ((1, "Ocak"), (10, "Ekim"), (12, "Aralık")):
        sayim = json.loads(json.dumps(ESKI))
        sayim["kaynak_manifest"]["indirme_zamani_utc"] = f"2027-{ay:02d}-01T00:00:00Z"
        assert f"1 {ad} 2027" in gorsel.render(sayim)


class TestCommand:
    def _veri(self, tmp_path: Path) -> Path:
        veri = tmp_path / "veri"
        veri.mkdir()
        (veri / "sayim.json").write_text(json.dumps(ESKI), encoding="utf-8")
        return veri

    def test_writes_the_chart(self, tmp_path, capsys):
        veri = self._veri(tmp_path)
        cikti = tmp_path / "out" / "c.svg"
        assert cli.main(["--veri", str(veri), "gorsel", "--cikti", str(cikti)]) == 0
        assert cikti.read_text(encoding="utf-8") == gorsel.render(ESKI)
        assert b"\r\n" not in cikti.read_bytes()

    def test_check_passes_when_identical_and_fails_when_stale(self, tmp_path, capsys):
        veri = self._veri(tmp_path)
        cikti = tmp_path / "c.svg"
        cli.main(["--veri", str(veri), "gorsel", "--cikti", str(cikti)])
        assert cli.main(["--veri", str(veri), "gorsel", "--cikti", str(cikti), "--denetle"]) == 0
        cikti.write_text("eski", encoding="utf-8")
        assert cli.main(["--veri", str(veri), "gorsel", "--cikti", str(cikti), "--denetle"]) == 1
        assert "uyuşmuyor" in capsys.readouterr().err

    def test_check_does_not_write(self, tmp_path, capsys):
        veri = self._veri(tmp_path)
        cikti = tmp_path / "yok.svg"
        assert cli.main(["--veri", str(veri), "gorsel", "--cikti", str(cikti), "--denetle"]) == 1
        assert not cikti.exists()

    def test_no_count_says_what_to_run(self, tmp_path, capsys):
        assert cli.main(["--veri", str(tmp_path / "bos"), "gorsel"]) == 2
        assert "mcp-census" in capsys.readouterr().err

    def test_broken_count_exits_two(self, tmp_path, capsys):
        veri = tmp_path / "veri"
        veri.mkdir()
        (veri / "sayim.json").write_text(json.dumps({"bulgular": []}), encoding="utf-8")
        assert cli.main(["--veri", str(veri), "gorsel", "--cikti", str(tmp_path / "x.svg")]) == 2
