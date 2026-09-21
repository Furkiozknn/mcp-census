# -*- coding: utf-8 -*-
"""CLI testleri: uçtan uca, ağa çıkmadan.

`indir` komutu ağa çıkan tek komut olduğu için burada sahte bir getirici ile
çalıştırılıyor; `say`, `rapor` ve `karsilastir` zaten ağ görmez.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from mcp_census import analyze, cli, fetch


def kayit(ad, surum="1.0.0", enson=True, depo=None, paketler=None):
    s = {"name": ad, "version": surum, "description": "yeterince uzun açıklama"}
    if depo:
        s["repository"] = {"url": depo}
    if paketler:
        s["packages"] = paketler
    return {
        "server": s,
        "_meta": {analyze.RESMI_META: {"status": "active", "isLatest": enson}},
    }


@pytest.fixture
def veri(tmp_path: Path) -> Path:
    d = tmp_path / "veri"
    fetch.jsonl_yaz(
        [
            kayit("a/b", "1.0.0", enson=False),
            kayit("a/b", "2.0.0", depo="https://github.com/a/b"),
            kayit("c/d", paketler=[{"registryType": "npm", "identifier": "x"}]),
        ],
        d / "kayitlar.jsonl",
    )
    fetch.manifest_yaz(
        {"kaynak": "sahte", "indirme_zamani_utc": "2026-01-01T00:00:00Z",
         "icerik_ozeti": "deadbeef", "tam_mi": True},
        d / "manifest.json",
    )
    return d


def test_say_sonra_rapor_calisir(veri: Path, capsys):
    assert cli.main(["--veri", str(veri), "say"]) == 0
    assert (veri / "sayim.json").exists()
    capsys.readouterr()

    assert cli.main(["--veri", str(veri), "rapor"]) == 0
    cikti = capsys.readouterr().out
    assert "MCP REGISTRY SAYIMI" in cikti
    assert "kayit_satiri" in cikti
    assert "TANIMLAR" in cikti


def test_say_veri_yoksa_2_doner(tmp_path: Path, capsys):
    assert cli.main(["--veri", str(tmp_path / "yok"), "say"]) == 2
    assert "Önce `mcp-census indir`" in capsys.readouterr().err


def test_rapor_sayim_yoksa_2_doner(veri: Path, capsys):
    assert cli.main(["--veri", str(veri), "rapor"]) == 2
    assert "Önce `mcp-census say`" in capsys.readouterr().err


def test_rapor_json_gecerli_json_basar(veri: Path, capsys):
    cli.main(["--veri", str(veri), "say"])
    capsys.readouterr()
    assert cli.main(["--veri", str(veri), "rapor", "--json"]) == 0
    s = json.loads(capsys.readouterr().out)
    assert {"bulgular", "dagilimlar", "en_cok_surum_yayinlayan"} <= set(s)


def test_rapor_manifesti_sayima_gomer(veri: Path, capsys):
    cli.main(["--veri", str(veri), "say"])
    capsys.readouterr()
    cli.main(["--veri", str(veri), "rapor"])
    assert "deadbeef" in capsys.readouterr().out, "künye rapora girmeli"


def test_indir_sahte_getirici_ile_dosya_yazar(tmp_path: Path, monkeypatch, capsys):
    govde = json.dumps({"servers": [kayit("a/b")], "metadata": {}}).encode()
    monkeypatch.setattr(fetch, "_istek", lambda url, zaman_asimi: govde)
    d = tmp_path / "v"
    assert cli.main(["--veri", str(d), "indir", "--sessiz"]) == 0
    assert fetch.jsonl_oku(d / "kayitlar.jsonl")
    manifest = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["tam_mi"] is True
    assert manifest["kayit_sayisi"] == 1


def test_kismi_indirme_manifestte_isaretlenir(tmp_path: Path, monkeypatch, capsys):
    """Kısmi indirme tam sayım gibi görünmemeli."""
    sayac = {"n": 0}

    def sahte(url, zaman_asimi):
        sayac["n"] += 1
        return json.dumps(
            {"servers": [kayit(f"a/{sayac['n']}")],
             "metadata": {"nextCursor": f"i{sayac['n']}"}}
        ).encode()

    monkeypatch.setattr(fetch, "_istek", sahte)
    d = tmp_path / "v"
    assert cli.main(["--veri", str(d), "indir", "--azami-sayfa", "2", "--sessiz"]) == 0
    manifest = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["tam_mi"] is False
    assert "TAM DEĞİL" in capsys.readouterr().err


def test_indir_registry_hatasinda_2_doner(tmp_path: Path, monkeypatch, capsys):
    def patla(url, zaman_asimi):
        return b"{bozuk"

    monkeypatch.setattr(fetch, "_istek", patla)
    assert cli.main(["--veri", str(tmp_path / "v"), "indir", "--sessiz"]) == 2


# --- karşılaştırma ---

def test_karsilastir_sadece_ekleme_0_doner(tmp_path: Path, capsys):
    a, b = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    fetch.jsonl_yaz([kayit("x/1")], a)
    fetch.jsonl_yaz([kayit("x/1"), kayit("x/2")], b)
    assert cli.main(["karsilastir", str(a), str(b)]) == 0
    cikti = capsys.readouterr().out
    assert "kaybolan 0" in cikti
    assert "+ x/2" in cikti


def test_karsilastir_kayip_varsa_1_doner(tmp_path: Path, capsys):
    """CI'da bir indirmenin eksik kalması sessizce geçmemeli."""
    a, b = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    fetch.jsonl_yaz([kayit("x/1"), kayit("x/2")], a)
    fetch.jsonl_yaz([kayit("x/1")], b)
    assert cli.main(["karsilastir", str(a), str(b)]) == 1
    assert "- x/2" in capsys.readouterr().out


def test_karsilastir_ayni_kumede_fark_yok(tmp_path: Path, capsys):
    a, b = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    fetch.jsonl_yaz([kayit("x/1")], a)
    fetch.jsonl_yaz([kayit("x/1", "9.9.9")], b)
    assert cli.main(["karsilastir", str(a), str(b)]) == 0
    s = analyze.karsilastir(fetch.jsonl_oku(a), fetch.jsonl_oku(b))
    assert s["eklenen_sayisi"] == 0 and s["kaybolan_sayisi"] == 0


def test_karsilastir_json_cikti(tmp_path: Path, capsys):
    a, b = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    fetch.jsonl_yaz([kayit("x/1")], a)
    fetch.jsonl_yaz([kayit("x/1"), kayit("x/2")], b)
    cli.main(["karsilastir", str(a), str(b), "--json"])
    s = json.loads(capsys.readouterr().out)
    assert s["yalnizca_ekleme_mi"] is True
    assert s["eklenen"] == ["x/2"]
