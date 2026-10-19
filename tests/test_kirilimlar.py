# -*- coding: utf-8 -*-
"""Breakdowns (install shape, per-server package and transport types,
namespace authority) and the series columns they feed."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from mcp_census import analyze

KOK = Path(__file__).resolve().parent.parent


def kayit(ad, *, paketler=None, uclar=None, enson=True):
    s = {"name": ad, "version": "1.0.0", "description": "yeterince uzun bir açıklama"}
    if paketler is not None:
        s["packages"] = paketler
    if uclar is not None:
        s["remotes"] = uclar
    return {"server": s, "_meta": {analyze.RESMI_META: {"status": "active", "isLatest": enson}}}


NPM = {"registryType": "npm", "identifier": "x"}
PYPI = {"registryType": "pypi", "identifier": "y"}
HTTP = {"type": "streamable-http", "url": "https://u"}
SSE = {"type": "sse", "url": "https://v"}


def _kayitlar():
    return [
        kayit("io.github.ali/a", paketler=[NPM]),
        kayit("io.github.ali/b", paketler=[NPM, NPM]),          # two npm packages, one server
        kayit("com.example/c", uclar=[HTTP, HTTP]),
        kayit("com.example/d", paketler=[PYPI], uclar=[SSE]),
        kayit("tek/e"),
    ]


def test_install_shape_partitions_the_latest_set():
    s = analyze.sayim(_kayitlar())
    shape = s["dagilimlar"]["kurulum_bicimi"]
    assert shape == {"yalnizca_paket": 2, "yalnizca_uzak": 1, "paket_ve_uzak": 1, "hicbiri": 1}
    n = next(b["deger"] for b in s["bulgular"] if b["ad"] == "en_son_surumler")
    assert sum(shape.values()) == n


def test_install_shape_agrees_with_existing_findings():
    s = analyze.sayim(_kayitlar())
    b = {x["ad"]: x["deger"] for x in s["bulgular"]}
    shape = s["dagilimlar"]["kurulum_bicimi"]
    assert shape["yalnizca_uzak"] == b["sadece_uzak_sunucu"]
    assert shape["hicbiri"] == b["ne_paket_ne_uc"]


def test_package_types_are_counted_per_server():
    d = analyze.sayim(_kayitlar())["dagilimlar"]
    assert d["paket_turu_sunucu"] == {"npm": 2, "pypi": 1}
    assert d["paket_turu"]["npm"] == 3, "per-package count stays as it was"
    assert d["uzak_uc_turu_sunucu"] == {"sse": 1, "streamable-http": 1}


@pytest.mark.parametrize("ad,beklenen", [
    ("io.github.ali/x", "io.github"),
    ("io.github/x", "io.github"),
    ("com.example/x", "alan_adi"),
    ("ai.bowmark/bowmark", "alan_adi"),
    ("tek/x", "diger"),
    ("adsiz", "diger"),
])
def test_namespace_kind(ad, beklenen):
    assert analyze.namespace_kind(kayit(ad)) == beklenen


def test_namespace_kind_counts_and_top_namespaces():
    d = analyze.sayim(_kayitlar())["dagilimlar"]
    assert d["ad_alani_turu"] == {"io.github": 2, "alan_adi": 2, "diger": 1}
    assert list(d["en_buyuk_ad_alanlari"].items())[:2] == [("com.example", 2), ("io.github.ali", 2)]


def test_top_namespaces_are_capped():
    kayitlar = [kayit(f"org{i}.example/s") for i in range(40)]
    d = analyze.sayim(kayitlar)["dagilimlar"]
    assert len(d["en_buyuk_ad_alanlari"]) == analyze.TOP_NAMESPACES


def test_new_breakdowns_do_not_depend_on_row_order():
    keys = ("kurulum_bicimi", "paket_turu_sunucu", "uzak_uc_turu_sunucu",
            "ad_alani_turu", "en_buyuk_ad_alanlari")
    a = analyze.sayim(_kayitlar())["dagilimlar"]
    b = analyze.sayim(list(reversed(_kayitlar())))["dagilimlar"]
    for key in keys:
        assert json.dumps(a[key]) == json.dumps(b[key]), key


class TestSeriesColumns:
    def _count(self, **dagilimlar):
        return {
            "bulgular": [{"ad": "kayit_satiri", "deger": 5, "tanim": "t"}],
            "dagilimlar": dagilimlar,
            "kaynak_manifest": {"indirme_zamani_utc": "2026-11-01T04:10:00Z", "tam_mi": True},
        }

    def test_new_columns_are_appended_after_the_original_nine(self):
        original = ("indirme_zamani_utc", "kayit_satiri", "ayri_sunucu_adi", "aktif_sunucu",
                    "deposuz_sunucu", "sadece_uzak_sunucu", "ne_paket_ne_uc", "kisa_aciklama",
                    "tek_surumlu_sunucu")
        assert analyze.SERI_SUTUNLARI[:9] == original
        assert set(analyze.SERI_DAGILIM_SUTUNLARI) == set(analyze.SERI_SUTUNLARI[9:])

    def test_distribution_values_fill_the_row(self):
        row = analyze.seri_satiri(self._count(
            kurulum_bicimi={"yalnizca_paket": 7, "paket_ve_uzak": 2},
            paket_turu_sunucu={"npm": 4},
            ad_alani_turu={"io.github": 6, "alan_adi": 3},
        ))
        assert row["yalnizca_paket"] == 7 and row["paket_ve_uzak"] == 2
        assert row["npm_sunucu"] == 4
        assert row["pypi_sunucu"] == 0, "the distribution exists, so a missing key is a real zero"
        assert row["io_github_ad_alani"] == 6 and row["alan_adi_ad_alani"] == 3

    def test_a_count_without_the_distribution_leaves_the_cell_empty(self):
        row = analyze.seri_satiri(self._count())
        for column in analyze.SERI_DAGILIM_SUTUNLARI:
            assert row[column] == "", column

    def test_the_committed_count_predates_the_breakdowns(self):
        s = analyze.sayim_oku(KOK / "veri" / "sayim.json")
        if "kurulum_bicimi" not in s["dagilimlar"]:
            assert analyze.seri_satiri(s)["yalnizca_paket"] == ""


class TestSeriesMigration:
    OLD_HEADER = ",".join(analyze.SERI_SUTUNLARI[:9])

    def test_an_older_file_is_widened_and_its_values_kept(self, tmp_path):
        yol = tmp_path / "zaman-serisi.csv"
        yol.write_text(self.OLD_HEADER + "\n2026-09-16T04:08:56Z,105038,32318,31972,7439,18183,425,286,20244\n",
                       encoding="utf-8")
        row = analyze.seri_satiri({
            "bulgular": [{"ad": "kayit_satiri", "deger": 9, "tanim": "t"}],
            "dagilimlar": {"kurulum_bicimi": {"yalnizca_paket": 1}},
            "kaynak_manifest": {"indirme_zamani_utc": "2026-11-01T04:10:00Z"},
        })
        assert analyze.seriye_ekle(yol, row) is True
        with open(yol, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert reader.fieldnames == list(analyze.SERI_SUTUNLARI)
        assert rows[0]["kayit_satiri"] == "105038" and rows[0]["tek_surumlu_sunucu"] == "20244"
        assert rows[0]["yalnizca_paket"] == "", "not measured then: empty, not zero"
        assert rows[1]["yalnizca_paket"] == "1"
        assert b"\r\n" not in yol.read_bytes()

    def test_a_foreign_header_is_refused_and_the_file_left_alone(self, tmp_path):
        yol = tmp_path / "zaman-serisi.csv"
        icerik = "indirme_zamani_utc,ayri_sunucu_adi,kayit_satiri\n2026-09-16T00:00:00Z,1,2\n"
        yol.write_text(icerik, encoding="utf-8")
        with pytest.raises(analyze.SayimHatasi, match="başı değil"):
            analyze.seriye_ekle(yol, {"indirme_zamani_utc": "2026-11-01T00:00:00Z"})
        assert yol.read_text(encoding="utf-8") == icerik

    def test_the_committed_series_uses_the_current_header(self):
        with open(KOK / "veri" / "zaman-serisi.csv", encoding="utf-8", newline="") as f:
            assert next(csv.reader(f)) == list(analyze.SERI_SUTUNLARI)


def test_the_sample_count_carries_the_breakdowns():
    s = analyze.sayim_oku(KOK / "veri" / "ornek" / "sayim.json")
    b = {x["ad"]: x["deger"] for x in s["bulgular"]}
    shape = s["dagilimlar"]["kurulum_bicimi"]
    assert sum(shape.values()) == b["en_son_surumler"]
    assert sum(s["dagilimlar"]["ad_alani_turu"].values()) == b["en_son_surumler"]
