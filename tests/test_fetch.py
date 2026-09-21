# -*- coding: utf-8 -*-
"""fetch.py testleri. Hiçbiri ağa çıkmaz: `getirici` sahte yanıt verir."""
from __future__ import annotations

import json
import urllib.error
from pathlib import Path

import pytest

from mcp_census import fetch


def sahte_sayfa(kayitlar, sonraki=None):
    govde = {"servers": kayitlar, "metadata": {"count": len(kayitlar)}}
    if sonraki:
        govde["metadata"]["nextCursor"] = sonraki
    return json.dumps(govde).encode("utf-8")


def kayit(ad, surum="1.0.0"):
    return {"server": {"name": ad, "version": surum}, "_meta": {}}


def test_tek_sayfa_okunur():
    def getirici(url, zaman_asimi):
        return sahte_sayfa([kayit("a/b")])

    sayfa = fetch.sayfa_getir(getirici=getirici)
    assert len(sayfa.kayitlar) == 1
    assert sayfa.sonraki_imlec is None


def test_imlec_zincirini_sonuna_kadar_takip_eder():
    sayfalar = {
        None: sahte_sayfa([kayit("a/1")], "imlec1"),
        "imlec1": sahte_sayfa([kayit("a/2")], "imlec2"),
        "imlec2": sahte_sayfa([kayit("a/3")]),
    }
    cagrilan = []

    def getirici(url, zaman_asimi):
        imlec = None
        if "cursor=" in url:
            imlec = url.split("cursor=")[1]
        cagrilan.append(imlec)
        return sayfalar[imlec]

    sonuc = fetch.indir(getirici=getirici)
    assert sonuc.manifest["kayit_sayisi"] == 3
    assert sonuc.manifest["sayfa_sayisi"] == 3
    assert cagrilan == [None, "imlec1", "imlec2"]


def test_tekrar_eden_imlec_sonsuz_donguyu_keser():
    """Registry aynı imleci iki kez verirse durmalı, sonsuza kadar çekmemeli."""

    def getirici(url, zaman_asimi):
        return sahte_sayfa([kayit("a/1")], "hep_ayni")

    with pytest.raises(fetch.RegistryHatasi, match="imleç tekrar etti"):
        fetch.indir(getirici=getirici)


def test_azami_sayfa_taniniyor():
    def getirici(url, zaman_asimi):
        # her seferinde farklı imleç: kendiliğinden hiç bitmez
        n = url.count("cursor=") and url.split("cursor=")[1] or "0"
        return sahte_sayfa([kayit(f"a/{n}")], f"i{len(n)}{n}")

    sonuc = fetch.indir(azami_sayfa=4, getirici=getirici)
    assert sonuc.manifest["sayfa_sayisi"] == 4
    assert sonuc.manifest["tam_mi"] is False


def test_4xx_yeniden_denenmez():
    denemeler = []

    def getirici(url, zaman_asimi):
        denemeler.append(url)
        raise urllib.error.HTTPError(url, 404, "yok", {}, None)

    with pytest.raises(fetch.RegistryHatasi, match="HTTP 404"):
        fetch.sayfa_getir(getirici=getirici)
    assert len(denemeler) == 1, "4xx kalıcı hatadır, tek deneme olmalı"


def test_5xx_yeniden_denenir_ve_sonunda_basarili_olur(monkeypatch):
    monkeypatch.setattr(fetch, "DENEME_BEKLEME", 0)
    denemeler = []

    def getirici(url, zaman_asimi):
        denemeler.append(url)
        if len(denemeler) < 3:
            raise urllib.error.HTTPError(url, 503, "mesgul", {}, None)
        return sahte_sayfa([kayit("a/b")])

    sayfa = fetch.sayfa_getir(getirici=getirici)
    assert len(sayfa.kayitlar) == 1
    assert len(denemeler) == 3


def test_bozuk_json_anlasilir_hata_verir():
    def getirici(url, zaman_asimi):
        return b"{bu json degil"

    with pytest.raises(fetch.RegistryHatasi, match="JSON değil"):
        fetch.sayfa_getir(getirici=getirici)


def test_servers_alani_yoksa_hata():
    def getirici(url, zaman_asimi):
        return json.dumps({"metadata": {}}).encode("utf-8")

    with pytest.raises(fetch.RegistryHatasi, match="'servers' listesi yok"):
        fetch.sayfa_getir(getirici=getirici)


def test_ozet_ayni_veride_ayni_farkli_veride_farkli():
    a = [kayit("x/y"), kayit("z/w")]
    b = [kayit("x/y"), kayit("z/w")]
    c = [kayit("x/y"), kayit("z/w", "2.0.0")]
    assert fetch.kayitlarin_ozeti(a) == fetch.kayitlarin_ozeti(b)
    assert fetch.kayitlarin_ozeti(a) != fetch.kayitlarin_ozeti(c)


def test_ozet_anahtar_sirasindan_etkilenmez():
    a = [{"server": {"name": "x", "version": "1"}}]
    b = [{"server": {"version": "1", "name": "x"}}]
    assert fetch.kayitlarin_ozeti(a) == fetch.kayitlarin_ozeti(b)


def test_jsonl_gidip_gelir(tmp_path: Path):
    kayitlar = [kayit("a/b"), kayit("c/d", "2.0.0")]
    yol = tmp_path / "alt" / "k.jsonl"
    fetch.jsonl_yaz(kayitlar, yol)
    assert fetch.jsonl_oku(yol) == kayitlar


def test_jsonl_bozuk_satirda_satir_numarasi_verir(tmp_path: Path):
    yol = tmp_path / "k.jsonl"
    yol.write_text('{"a":1}\n{bozuk}\n', encoding="utf-8")
    with pytest.raises(fetch.RegistryHatasi, match=r":2 okunamadı"):
        fetch.jsonl_oku(yol)


def test_turkce_karakter_korunur(tmp_path: Path):
    kayitlar = [{"server": {"name": "a/b", "description": "ölçüm ve şehir"}}]
    yol = tmp_path / "k.jsonl"
    fetch.jsonl_yaz(kayitlar, yol)
    assert fetch.jsonl_oku(yol)[0]["server"]["description"] == "ölçüm ve şehir"
