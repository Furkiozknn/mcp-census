# -*- coding: utf-8 -*-
"""Bozuk, eksik ya da kötü niyetli girdide davranış.

Buradaki her test gerçek bir kusura karşı yazıldı: bu dosyadan önce
aşağıdaki girdilerin çoğu kullanıcıya bir Python yığın izi (traceback)
gösteriyordu, `--surum` veri klasörünün dışına yazdırabiliyordu, `--taban`
`file://` adreslerini açıyordu ve kısmi bir indirme zaman serisine
girebiliyordu.
"""
from __future__ import annotations

import gzip
import io
import json
import re
from pathlib import Path

import pytest

from mcp_census import __version__, analyze, cli, fetch

KOK = Path(__file__).resolve().parent.parent


def kayit(ad, surum="1.0.0"):
    return {
        "server": {"name": ad, "version": surum, "description": "yeterince uzun açıklama"},
        "_meta": {analyze.RESMI_META: {"status": "active", "isLatest": True}},
    }


def tam_sayim(veri: Path, zaman="2026-10-01T04:10:00Z", tam=True, **manifest) -> Path:
    """`say` çıktısını taklit eden, künyeli bir sayim.json yazar."""
    s = analyze.sayim([kayit("a/b"), kayit("c/d")])
    s["kaynak_manifest"] = {"indirme_zamani_utc": zaman, "tam_mi": tam,
                            "kayit_sayisi": 2, "sayfa_sayisi": 1, **manifest}
    analyze.sayimi_yaz(s, veri / "sayim.json")
    return veri / "sayim.json"


# --- fetch: registry yanıtı ------------------------------------------------

@pytest.mark.parametrize("taban", ["file:///etc", "ftp://ornek.org", "registry.org", "http://"])
def test_http_disi_taban_hic_istek_atmadan_reddedilir(taban):
    cagrildi = []

    def getirici(url, zaman_asimi):
        cagrildi.append(url)
        return b"{}"

    with pytest.raises(fetch.RegistryHatasi, match="http"):
        fetch.sayfa_getir(taban=taban, getirici=getirici)
    assert not cagrildi


def test_https_taban_sondaki_egik_cizgiyi_tolere_eder():
    urller = []

    def getirici(url, zaman_asimi):
        urller.append(url)
        return json.dumps({"servers": []}).encode()

    fetch.sayfa_getir(taban="https://ornek.org/", getirici=getirici)
    assert urller == ["https://ornek.org/v0/servers?limit=100"]


def test_sifir_sayfa_boyu_reddedilir():
    with pytest.raises(fetch.RegistryHatasi, match="en az 1"):
        fetch.sayfa_getir(limit=0, getirici=lambda u, z: b"{}")


@pytest.mark.parametrize("govde", [b"[]", b'"metin"', b"null"])
def test_nesne_olmayan_yanit_anlasilir_hata_verir(govde):
    with pytest.raises(fetch.RegistryHatasi, match="JSON nesnesi değil"):
        fetch.sayfa_getir(getirici=lambda u, z: govde)


def test_nesne_olmayan_kayit_diske_yazilmadan_reddedilir():
    govde = json.dumps({"servers": [kayit("a/b"), 7]}).encode()
    with pytest.raises(fetch.RegistryHatasi, match=r"'servers'\[1\]"):
        fetch.sayfa_getir(getirici=lambda u, z: govde)


def test_nesne_olmayan_metadata_imleci_yok_sayar():
    govde = json.dumps({"servers": [], "metadata": "bozuk"}).encode()
    assert fetch.sayfa_getir(getirici=lambda u, z: govde).sonraki_imlec is None


class _SahteYanit:
    def __init__(self, govde: bytes, kodlama: str | None = None):
        self._akim = io.BytesIO(govde)
        self.headers = {"Content-Encoding": kodlama} if kodlama else {}

    def read(self, n=-1):
        return self._akim.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_gzip_yanit_acilir(monkeypatch):
    govde = json.dumps({"servers": []}).encode()
    monkeypatch.setattr(fetch.urllib.request, "urlopen",
                        lambda istek, timeout: _SahteYanit(gzip.compress(govde), "gzip"))
    assert fetch._istek("https://ornek.org", 1.0) == govde


def test_gzip_bombasi_bellegi_doldurmadan_reddedilir(monkeypatch):
    """Sıkıştırılmış hâli küçük, açılmış hâli tavanı aşan yanıt."""
    bomba = gzip.compress(b"\0" * 10_000)
    assert len(bomba) < 1_000
    monkeypatch.setattr(fetch, "AZAMI_YANIT_BAYT", 1_000)
    monkeypatch.setattr(fetch.urllib.request, "urlopen",
                        lambda istek, timeout: _SahteYanit(bomba, "gzip"))
    with pytest.raises(fetch.RegistryHatasi, match="aşıyor"):
        fetch._istek("https://ornek.org", 1.0)


def test_asiri_buyuk_ham_yanit_reddedilir(monkeypatch):
    monkeypatch.setattr(fetch, "AZAMI_YANIT_BAYT", 100)
    monkeypatch.setattr(fetch.urllib.request, "urlopen",
                        lambda istek, timeout: _SahteYanit(b"x" * 101))
    with pytest.raises(fetch.RegistryHatasi, match="aşıyor"):
        fetch._istek("https://ornek.org", 1.0)


def test_jsonl_nesne_olmayan_satirda_satir_numarasi_verir(tmp_path: Path):
    yol = tmp_path / "k.jsonl"
    yol.write_text('{"a": 1}\n[1, 2]\n', encoding="utf-8")
    with pytest.raises(fetch.RegistryHatasi, match=r"k\.jsonl:2 bir JSON nesnesi değil"):
        fetch.jsonl_oku(yol)


# --- cli: argümanlar ---------------------------------------------------------

@pytest.mark.parametrize("deger", ["../../kacis", "a/b", "..", ".gizli", "a..b", "x" * 65, ""])
def test_surum_suzgeci_dosya_adina_yol_sokamaz(tmp_path: Path, monkeypatch, deger):
    monkeypatch.setattr(fetch, "_istek", lambda u, z: pytest.fail("ağa çıkılmamalı"))
    with pytest.raises(SystemExit) as e:
        cli.main(["--veri", str(tmp_path / "v"), "indir", "--surum", deger])
    assert e.value.code == 2
    assert not any(tmp_path.rglob("*.jsonl"))


@pytest.mark.parametrize("deger", ["latest", "1.2.3", "2.0.0-rc.1", "1.0+yerel"])
def test_gecerli_surum_suzgeci_kabul_edilir(tmp_path: Path, monkeypatch, deger):
    govde = json.dumps({"servers": [kayit("a/b")]}).encode()
    monkeypatch.setattr(fetch, "_istek", lambda u, z: govde)
    d = tmp_path / "v"
    assert cli.main(["--veri", str(d), "indir", "--sessiz", "--surum", deger]) == 0
    assert (d / f"kayitlar-{deger}.jsonl").is_file()


@pytest.mark.parametrize("arguman", [["--azami-sayfa", "0"], ["--sayfa-boyu", "0"],
                                     ["--azami-sayfa", "iki"], ["--taban", "file:///etc"]])
def test_gecersiz_indir_argumani_ag_gormeden_reddedilir(tmp_path, monkeypatch, capsys, arguman):
    monkeypatch.setattr(fetch, "_istek", lambda u, z: pytest.fail("ağa çıkılmamalı"))
    with pytest.raises(SystemExit) as e:
        cli.main(["--veri", str(tmp_path), "indir", *arguman])
    assert e.value.code == 2


def test_version_pyproject_ile_ayni(capsys):
    beyan = re.search(r'^version = "([^"]+)"',
                      (KOK / "pyproject.toml").read_text(encoding="utf-8"), re.M).group(1)
    assert __version__ == beyan
    with pytest.raises(SystemExit) as e:
        cli.main(["--version"])
    assert e.value.code == 0
    assert capsys.readouterr().out.strip() == f"mcp-census {beyan}"


# --- cli: bozuk dosyalar yığın izi değil, çıkış 2 ------------------------------

def _hata_satiri(capsys) -> str:
    err = capsys.readouterr().err
    assert "Traceback" not in err
    assert err.startswith("hata: ")
    return err


def test_karsilastir_olmayan_dosyada_2_doner(tmp_path: Path, capsys):
    var = tmp_path / "var.jsonl"
    fetch.jsonl_yaz([kayit("a/b")], var)
    assert cli.main(["karsilastir", str(var), str(tmp_path / "yok.jsonl")]) == 2
    assert "yok.jsonl" in _hata_satiri(capsys)


def test_say_bozuk_kayitta_2_doner(tmp_path: Path, capsys):
    (tmp_path / "kayitlar.jsonl").write_text("{bozuk\n", encoding="utf-8")
    assert cli.main(["--veri", str(tmp_path), "say"]) == 2
    assert "kayitlar.jsonl:1" in _hata_satiri(capsys)


@pytest.mark.parametrize("icerik", ["{bozuk", "[1, 2]"])
def test_say_bozuk_manifestte_2_doner_ve_sayim_yazmaz(tmp_path: Path, capsys, icerik):
    fetch.jsonl_yaz([kayit("a/b")], tmp_path / "kayitlar.jsonl")
    (tmp_path / "manifest.json").write_text(icerik, encoding="utf-8")
    assert cli.main(["--veri", str(tmp_path), "say"]) == 2
    assert "manifest.json" in _hata_satiri(capsys)
    assert not (tmp_path / "sayim.json").exists()


@pytest.mark.parametrize("icerik", ["{bozuk", "[]", '{"a": 1}',
                                    '{"bulgular": [{"ad": "x"}]}',
                                    '{"bulgular": [], "dagilimlar": {"durum": [1]}}'])
def test_rapor_bozuk_sayimda_2_doner(tmp_path: Path, capsys, icerik):
    (tmp_path / "sayim.json").write_text(icerik, encoding="utf-8")
    assert cli.main(["--veri", str(tmp_path), "rapor"]) == 2
    assert "sayim.json" in _hata_satiri(capsys)


def test_depodaki_sayimlar_dogrulamadan_geciyor():
    """Doğrulama gerçek dosyaları reddedecek kadar katı olmamalı."""
    for yol in (KOK / "veri" / "sayim.json", KOK / "veri" / "ornek" / "sayim.json"):
        assert analyze.sayim_oku(yol)["bulgular"]


# --- seri: yalnızca tam sayımlar seriye girer -----------------------------------

def test_seri_kismi_sayimi_reddeder_ve_csv_yazmaz(tmp_path: Path, capsys):
    """`--azami-sayfa 5` ile yapılan bir deneme ayın satırı olmamalı."""
    tam_sayim(tmp_path, tam=False)
    assert cli.main(["--veri", str(tmp_path), "seri"]) == 2
    assert "kısmi" in _hata_satiri(capsys)
    assert not (tmp_path / "zaman-serisi.csv").exists()


def test_seri_kunyesiz_sayimi_reddeder(tmp_path: Path, capsys):
    analyze.sayimi_yaz(analyze.sayim([kayit("a/b")]), tmp_path / "sayim.json")
    assert cli.main(["--veri", str(tmp_path), "seri"]) == 2
    assert "kaynak_manifest" in _hata_satiri(capsys)


def test_seri_depodaki_ornek_kismi_oldugu_icin_reddedilir(tmp_path: Path, capsys):
    s = analyze.sayim_oku(KOK / "veri" / "ornek" / "sayim.json")
    s["kaynak_manifest"] = json.loads(
        (KOK / "veri" / "ornek" / "manifest.json").read_text(encoding="utf-8"))
    analyze.sayimi_yaz(s, tmp_path / "sayim.json")
    assert cli.main(["--veri", str(tmp_path), "seri"]) == 2


def test_seri_tam_sayimi_ekler_ozeti_yazar_ve_tekrarda_eklemez(tmp_path: Path, capsys):
    onceki = tmp_path / "onceki.json"
    tam_sayim(tmp_path, zaman="2026-09-01T04:10:00Z")
    (tmp_path / "sayim.json").rename(onceki)
    tam_sayim(tmp_path, zaman="2026-10-01T04:10:00Z")
    ozet = tmp_path / "ozet.md"
    ozet.write_text("onceden var\n", encoding="utf-8")

    arg = ["--veri", str(tmp_path), "seri", "--onceki", str(onceki), "--ozet", str(ozet)]
    assert cli.main(arg) == 0
    cikti = capsys.readouterr().out
    assert "Seriye satir eklendi: **evet**" in cikti
    assert "| `kayit_satiri` | 2 | 2 | 0 |" in cikti
    metin = ozet.read_text(encoding="utf-8")
    assert metin.startswith("onceden var\n"), "özet dosyasının üstüne yazılmamalı"
    assert metin.endswith(cikti)

    satirlar = (tmp_path / "zaman-serisi.csv").read_text(encoding="utf-8").splitlines()
    assert satirlar[0] == ",".join(analyze.SERI_SUTUNLARI)
    assert satirlar[1].startswith("2026-10-01T04:10:00Z,2,2,")

    assert cli.main(arg) == 0
    assert "hayir, ayni damga zaten var" in capsys.readouterr().out
    assert len((tmp_path / "zaman-serisi.csv").read_text(encoding="utf-8").splitlines()) == 2


def test_seri_ozeti_is_akisinin_eski_bicimini_koruyor():
    """Özet, iş akışının içindeki satır içi Python'dan taşındı; biçim aynı kalmalı."""
    yeni = {"kaynak_manifest": {"indirme_zamani_utc": "Z", "kayit_sayisi": 5, "sayfa_sayisi": 1}}
    fark = {"olcutler": [{"ad": "a", "onceki": 1, "simdiki": 3, "fark": 2},
                         {"ad": "b", "onceki": 3, "simdiki": 1, "fark": -2}],
            "yeni_olcutler": ["c"], "dusen_olcutler": []}
    assert analyze.seri_ozeti(fark, yeni, False) == (
        "### Sayim\n\nIndirme: `Z`, 5 satir, 1 sayfa.\n\n"
        "| olcut | onceki | simdiki | fark |\n| --- | ---: | ---: | ---: |\n"
        "| `a` | 1 | 3 | +2 |\n| `b` | 3 | 1 | -2 |\n\n"
        "Yeni olcut: `c`\n\nSeriye satir eklendi: **hayir, ayni damga zaten var**\n"
    )


def test_sayim_farki_sayi_olmayan_degerde_cokmez():
    e = {"bulgular": [{"ad": "x", "deger": "12"}, {"ad": "y", "deger": 1}]}
    y = {"bulgular": [{"ad": "x", "deger": 13}, {"ad": "y", "deger": 2}]}
    f = analyze.sayim_farki(e, y)
    assert [o["ad"] for o in f["olcutler"]] == ["y"]


# --- iş akışı: girdiler kabuğa metin olarak gömülmez ---------------------------

def test_sayim_is_akisi_girdiyi_kabuga_gommez_ve_kismi_kosuyu_commit_etmez():
    metin = (KOK / ".github" / "workflows" / "sayim.yml").read_text(encoding="utf-8")
    # `${{ ... }}` bir `run:` betiğinin içine metin olarak yapıştırılırsa, iş
    # akışını tetikleyen kişinin yazdığı değer kabuk komutu olarak çalışır.
    for satir in metin.splitlines():
        if "${{" in satir and "inputs" in satir:
            assert re.match(r"\s*(if:|[A-Z_]+:)", satir), satir
    # Seri ve commit adımları yalnızca tam indirmede koşar.
    assert "mcp-census --veri veri seri" in metin
    assert metin.count("if: steps.indir.outputs.tam == 'true'") == 2
    assert 'echo "tam=true"' in metin and "--azami-sayfa" in metin


def test_yazilamayan_rapor_yolu_yigin_izi_degil_2_doner(tmp_path: Path, capsys):
    tam_sayim(tmp_path)
    engel = tmp_path / "dosya"
    engel.write_text("bir klasör değil", encoding="utf-8")
    assert cli.main(["--veri", str(tmp_path), "rapor", "--yaz", str(engel / "r.txt")]) == 2
    assert "dosya" in _hata_satiri(capsys)
