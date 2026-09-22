# -*- coding: utf-8 -*-
"""analyze.py testleri.

Buradaki testlerin çoğu tek bir şeyi koruyor: sayının **tanımı**. Bir sayım
aracında asıl kırılgan yer aritmetik değil, "sunucu" kelimesinin ne demek
olduğunun sessizce kaymasıdır.
"""
from __future__ import annotations

from mcp_census import analyze


def kayit(ad, surum="1.0.0", *, durum="active", enson=False,
          depo=None, paketler=None, uclar=None, aciklama="yeterince uzun bir açıklama"):
    s = {"name": ad, "version": surum, "description": aciklama}
    if depo is not None:
        s["repository"] = depo
    if paketler is not None:
        s["packages"] = paketler
    if uclar is not None:
        s["remotes"] = uclar
    return {
        "server": s,
        "_meta": {analyze.RESMI_META: {"status": durum, "isLatest": enson}},
    }


# --- alan okuyucular: bozuk kayıt patlatmamalı ---

def test_bozuk_kayitlar_cokmeye_yol_acmaz():
    bozuklar = [{}, {"server": None}, {"server": []}, {"server": {}, "_meta": "x"}]
    for k in bozuklar:
        assert analyze.ad(k) == ""
        assert analyze.durum(k) == "bilinmiyor"
        assert analyze.depo_urlsi(k) is None
        assert analyze.paketler(k) == []
        assert analyze.uzak_uclar(k) == []


def test_depo_urlsi_iki_bicimi_de_okur():
    assert analyze.depo_urlsi(kayit("a/b", depo={"url": "https://x/y"})) == "https://x/y"
    assert analyze.depo_urlsi(kayit("a/b", depo="https://x/z")) == "https://x/z"
    assert analyze.depo_urlsi(kayit("a/b", depo={})) is None
    assert analyze.depo_urlsi(kayit("a/b")) is None


def test_sadece_uzak_tanimi():
    sadece_uzak = kayit("a/b", uclar=[{"type": "streamable-http", "url": "https://u"}])
    paketli = kayit("c/d", paketler=[{"registryType": "npm", "identifier": "x"}])
    ikisi = kayit("e/f",
                  uclar=[{"type": "sse", "url": "https://u"}],
                  paketler=[{"registryType": "npm", "identifier": "x"}])
    assert analyze.sadece_uzak_mi(sadece_uzak) is True
    assert analyze.sadece_uzak_mi(paketli) is False
    assert analyze.sadece_uzak_mi(ikisi) is False, "paketi varsa sadece-uzak değildir"


# --- en son sürüme indirgeme ---

def test_isLatest_isaretli_olan_kazanir():
    kayitlar = [
        kayit("a/b", "1.0.0", enson=False),
        kayit("a/b", "3.0.0", enson=True),
        kayit("a/b", "2.0.0", enson=False),
    ]
    sonuc = analyze.en_son_kayitlar(kayitlar)
    assert len(sonuc) == 1
    assert analyze.surum(sonuc[0]) == "3.0.0"


def test_isLatest_yoksa_en_son_gorulen_alinir():
    kayitlar = [kayit("a/b", "1.0.0"), kayit("a/b", "1.0.1")]
    sonuc = analyze.en_son_kayitlar(kayitlar)
    assert analyze.surum(sonuc[0]) == "1.0.1"


def test_isaretli_kayit_sonradan_gelen_isaretsizle_ezilmez():
    kayitlar = [kayit("a/b", "9.0.0", enson=True), kayit("a/b", "1.0.0", enson=False)]
    sonuc = analyze.en_son_kayitlar(kayitlar)
    assert analyze.surum(sonuc[0]) == "9.0.0"


def test_adsiz_kayitlar_atilir():
    assert analyze.en_son_kayitlar([{}, {"server": {"name": ""}}]) == []


# --- sayımın kendisi ---

def _bulgu(sonuc, ad):
    for b in sonuc["bulgular"]:
        if b["ad"] == ad:
            return b
    raise AssertionError(f"bulgu yok: {ad}")


def test_satir_sayisi_ile_sunucu_sayisi_ayri_raporlanir():
    """Bu deponun var olma sebebi olan ayrım."""
    kayitlar = [
        kayit("a/b", "1.0.0"),
        kayit("a/b", "1.0.1"),
        kayit("a/b", "1.0.2"),
        kayit("c/d", "1.0.0"),
    ]
    sonuc = analyze.sayim(kayitlar)
    assert _bulgu(sonuc, "kayit_satiri")["deger"] == 4
    assert _bulgu(sonuc, "ayri_sunucu_adi")["deger"] == 2
    assert _bulgu(sonuc, "en_son_surumler")["deger"] == 2


def test_deposuz_sunucu_sayilir():
    kayitlar = [
        kayit("a/b", depo={"url": "https://github.com/a/b"}),
        kayit("c/d"),
        kayit("e/f"),
    ]
    b = _bulgu(analyze.sayim(kayitlar), "deposuz_sunucu")
    assert b["deger"] == 2
    assert b["payda"] == 3
    assert b["yuzde"] == 66.7


def test_ne_paket_ne_uc_sayilir():
    kayitlar = [
        kayit("a/b", paketler=[{"registryType": "npm", "identifier": "x"}]),
        kayit("c/d", uclar=[{"type": "sse", "url": "https://u"}]),
        kayit("e/f"),
    ]
    assert _bulgu(analyze.sayim(kayitlar), "ne_paket_ne_uc")["deger"] == 1


def test_kisa_aciklama_esigi():
    kayitlar = [kayit("a/b", aciklama="kısa"), kayit("c/d", aciklama="x" * 25)]
    assert _bulgu(analyze.sayim(kayitlar), "kisa_aciklama")["deger"] == 1


def test_dagilimlar_en_son_surumler_uzerinden_sayilir():
    """Sürüm satırları dağılımı şişirmemeli."""
    kayitlar = [
        kayit("a/b", "1.0.0", paketler=[{"registryType": "npm", "identifier": "x"}]),
        kayit("a/b", "2.0.0", enson=True,
              paketler=[{"registryType": "npm", "identifier": "x"}]),
        kayit("c/d", "1.0.0", paketler=[{"registryType": "pypi", "identifier": "y"}]),
    ]
    d = analyze.sayim(kayitlar)["dagilimlar"]["paket_turu"]
    assert d == {"npm": 1, "pypi": 1}, "aynı sunucunun iki sürümü iki kez sayılmamalı"


def test_durum_dagilimi():
    kayitlar = [kayit("a/b"), kayit("c/d", durum="deleted"), kayit("e/f")]
    sonuc = analyze.sayim(kayitlar)
    assert sonuc["dagilimlar"]["durum"] == {"active": 2, "deleted": 1}
    assert _bulgu(sonuc, "aktif_sunucu")["deger"] == 2


def test_barindirici_dagilimi_alan_adina_gore():
    kayitlar = [
        kayit("a/b", depo={"url": "https://github.com/a/b"}),
        kayit("c/d", depo={"url": "https://gitlab.com/c/d"}),
        kayit("e/f", depo={"url": "https://github.com/e/f"}),
    ]
    d = analyze.sayim(kayitlar)["dagilimlar"]["depo_barindiricisi"]
    assert d["github.com"] == 2 and d["gitlab.com"] == 1


def test_en_cok_surum_yayinlayan_siralanir():
    kayitlar = (
        [kayit("cok/surum", f"1.0.{i}") for i in range(5)]
        + [kayit("az/surum", "1.0.0")]
    )
    ilk = analyze.sayim(kayitlar)["en_cok_surum_yayinlayan"][0]
    assert ilk == {"ad": "cok/surum", "surum_sayisi": 5}


def test_yuzdeler_paydasiz_bulguda_none():
    b = analyze.Bulgu("x", 5, "tanım")
    assert b.yuzde is None
    assert analyze.Bulgu("x", 5, "t", payda=0).yuzde is None


def test_bos_girdide_cokmez():
    sonuc = analyze.sayim([])
    assert _bulgu(sonuc, "kayit_satiri")["deger"] == 0
    assert _bulgu(sonuc, "en_son_surumler")["deger"] == 0


def test_her_bulgu_tanim_tasir():
    """Tanımsız sayı üretilmemeli — deponun temel kuralı."""
    kayitlar = [kayit("a/b"), kayit("c/d", "2.0.0")]
    for b in analyze.sayim(kayitlar)["bulgular"]:
        assert b["tanim"].strip(), f"{b['ad']} tanımsız"
        assert len(b["tanim"]) > 15, f"{b['ad']} tanımı fazla kısa"


def test_paydali_bulgularda_deger_paydayi_asmaz():
    """Koruma yasası: bir alt küme, kümesinden büyük olamaz."""
    kayitlar = [
        kayit("a/b", "1.0.0"),
        kayit("a/b", "1.0.1"),
        kayit("c/d", depo={"url": "https://github.com/c/d"}),
        kayit("e/f", uclar=[{"type": "sse", "url": "https://u"}]),
    ]
    for b in analyze.sayim(kayitlar)["bulgular"]:
        if b["payda"]:
            assert b["deger"] <= b["payda"], f"{b['ad']}: {b['deger']} > {b['payda']}"


# --------------------------------------------------------------------------
# zaman serisi
# --------------------------------------------------------------------------


def _sayim(zaman: str, **olcutler) -> dict:
    return {
        "kaynak_manifest": {"indirme_zamani_utc": zaman},
        "bulgular": [
            {"ad": ad, "deger": deger, "tanim": "test", "payda": None, "yuzde": None}
            for ad, deger in olcutler.items()
        ],
    }


def test_sayim_farki_olcut_olcut_karsilastiriyor():
    f = analyze.sayim_farki(
        _sayim("2026-01-01T00:00:00Z", aktif_sunucu=100, deposuz_sunucu=10),
        _sayim("2026-02-01T00:00:00Z", aktif_sunucu=120, deposuz_sunucu=10),
    )
    d = {o["ad"]: o for o in f["olcutler"]}
    assert d["aktif_sunucu"]["fark"] == 20
    assert d["aktif_sunucu"]["yuzde"] == 20.0
    assert d["deposuz_sunucu"]["fark"] == 0
    assert f["hareketli_sayisi"] == 1
    assert f["degisti_mi"] is True


def test_hicbir_sey_degismediyse_degisti_mi_yanlis():
    s = _sayim("2026-01-01T00:00:00Z", aktif_sunucu=100)
    assert analyze.sayim_farki(s, s)["degisti_mi"] is False


def test_yeni_ve_dusen_olcutler_adiyla_bildiriliyor():
    f = analyze.sayim_farki(
        _sayim("2026-01-01T00:00:00Z", eski_olcut=1),
        _sayim("2026-02-01T00:00:00Z", yeni_olcut=1),
    )
    assert f["yeni_olcutler"] == ["yeni_olcut"]
    assert f["dusen_olcutler"] == ["eski_olcut"]
    assert f["degisti_mi"] is True


def test_sifirdan_buyumede_yuzde_uydurulmuyor():
    f = analyze.sayim_farki(
        _sayim("2026-01-01T00:00:00Z", x=0),
        _sayim("2026-02-01T00:00:00Z", x=5),
    )
    o = f["olcutler"][0]
    assert o["fark"] == 5
    assert o["yuzde"] is None


def test_seri_satiri_sutunlari_dolduruyor():
    s = _sayim("2026-01-01T00:00:00Z", kayit_satiri=10, aktif_sunucu=5)
    satir = analyze.seri_satiri(s)
    assert satir["indirme_zamani_utc"] == "2026-01-01T00:00:00Z"
    assert satir["kayit_satiri"] == 10
    assert satir["aktif_sunucu"] == 5


def test_olculmeyen_olcut_sifira_cevrilmiyor():
    """Bir seride "o gün ölçülmedi" ile "o gün sıfırdı" aynı şey değildir."""
    satir = analyze.seri_satiri(_sayim("2026-01-01T00:00:00Z", kayit_satiri=10))
    assert satir["aktif_sunucu"] == ""
    assert satir["aktif_sunucu"] != 0


def test_seriye_ekleme_basliği_bir_kez_yaziyor(tmp_path):
    yol = tmp_path / "seri.csv"
    assert analyze.seriye_ekle(yol, analyze.seri_satiri(_sayim("2026-01-01T00:00:00Z", kayit_satiri=1)))
    assert analyze.seriye_ekle(yol, analyze.seri_satiri(_sayim("2026-02-01T00:00:00Z", kayit_satiri=2)))
    satirlar = yol.read_text(encoding="utf-8").strip().splitlines()
    assert len(satirlar) == 3
    assert satirlar[0].startswith("indirme_zamani_utc,")


def test_ayni_damga_iki_kez_eklenmiyor(tmp_path):
    yol = tmp_path / "seri.csv"
    satir = analyze.seri_satiri(_sayim("2026-01-01T00:00:00Z", kayit_satiri=1))
    assert analyze.seriye_ekle(yol, satir) is True
    assert analyze.seriye_ekle(yol, satir) is False
    assert len(yol.read_text(encoding="utf-8").strip().splitlines()) == 2


def test_damgasiz_satir_reddediliyor(tmp_path):
    import pytest as _pytest

    with _pytest.raises(ValueError):
        analyze.seriye_ekle(tmp_path / "seri.csv", {"kayit_satiri": 1})


def test_sutun_sirasi_sabit(tmp_path):
    """Sütun sırası değişirse eski satırlar okunamaz hâle gelir."""
    assert analyze.SERI_SUTUNLARI[0] == "indirme_zamani_utc"
    assert "aktif_sunucu" in analyze.SERI_SUTUNLARI
    yol = tmp_path / "seri.csv"
    analyze.seriye_ekle(yol, analyze.seri_satiri(_sayim("2026-01-01T00:00:00Z", kayit_satiri=1)))
    basliklar = yol.read_text(encoding="utf-8").splitlines()[0].split(",")
    assert basliklar == list(analyze.SERI_SUTUNLARI)


def test_gercek_sayim_dosyasindan_satir_cikiyor():
    from pathlib import Path as _P

    yol = _P(__file__).resolve().parents[1] / "veri" / "sayim.json"
    if not yol.is_file():
        return
    import json as _json

    satir = analyze.seri_satiri(_json.loads(yol.read_text(encoding="utf-8")))
    assert satir["indirme_zamani_utc"]
    assert isinstance(satir["kayit_satiri"], int)
