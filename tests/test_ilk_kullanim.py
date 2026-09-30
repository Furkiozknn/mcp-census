# -*- coding: utf-8 -*-
"""İlk kullanıcının gördükleri: yardım, kullanım hataları, yanlış klasör.

Çıkış kodları ve çıktı sözleşmesi test_cli / test_saglamlik'te korunuyor; burada
yalnızca mesajların *söylediği* şey sınanıyor: hata satırı `hata: ` ile başlar,
Türkçedir ve bir sonraki adımı (yazılacak komutu) verir.
"""
from __future__ import annotations

import re
import shlex
from pathlib import Path

import pytest

from mcp_census import cli, fetch

KOK = Path(__file__).resolve().parent.parent


def _calistir(argv, capsys):
    try:
        kod = cli.main(argv)
    except SystemExit as e:
        kod = e.code
    cikti = capsys.readouterr()
    return kod, cikti.out, cikti.err


# --- --veri komuttan sonra da yazılabilir ------------------------------------

def test_veri_komuttan_sonra_yazilabilir(capsys):
    kod, cikti, _ = _calistir(["rapor", "--veri", str(KOK / "veri" / "ornek")], capsys)
    assert kod == 0
    assert "MCP REGISTRY SAYIMI" in cikti


def test_veri_komuttan_once_ve_sonra_ayni_sonucu_verir(capsys):
    ornek = str(KOK / "veri" / "ornek")
    _, once, _ = _calistir(["--veri", ornek, "rapor"], capsys)
    _, sonra, _ = _calistir(["rapor", "--veri", ornek], capsys)
    assert once == sonra


def test_veri_verilmezse_varsayilan_veri_kalir(capsys, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    kod, _, err = _calistir(["rapor"], capsys)
    assert kod == 2
    assert "veri" in err


# --- kullanım hataları: Türkçe, tek biçim, yardım gösterir ---------------------

@pytest.mark.parametrize("argv, beklenen, yardim", [
    ([], "eksik argüman: komut", "`mcp-census --help`"),
    (["nope"], "bilinmeyen komut 'nope'", "`mcp-census --help`"),
    (["karsilastir", "x"], "eksik argüman: yeni", "`mcp-census karsilastir --help`"),
    (["indir", "--azami-sayfa", "0"], "--azami-sayfa: en az 1", "`mcp-census indir --help`"),
    (["indir", "--veri"], "--veri bir değer bekliyor", "`mcp-census indir --help`"),
])
def test_kullanim_hatasi_turkce_ve_yardim_gosterir(capsys, argv, beklenen, yardim):
    kod, out, err = _calistir(argv, capsys)
    assert kod == 2
    assert out == ""
    assert err.startswith("hata: "), err
    assert beklenen in err
    assert yardim in err
    assert "Traceback" not in err
    # argparse'in İngilizce iskeleti sızmamalı
    for ingilizce in ("the following", "unrecognized", "invalid choice", "error:"):
        assert ingilizce not in err


def test_tanınmayan_arguman_turkce(capsys):
    kod, _, err = _calistir(["rapor", "--nope"], capsys)
    assert kod == 2
    assert "tanınmayan argüman: --nope" in err


def test_yardim_turkce_ve_ornek_iceriyor(capsys):
    kod, out, _ = _calistir(["--help"], capsys)
    assert kod == 0
    assert "kullanım: mcp-census" in out
    assert "hızlı başlangıç" in out
    assert "mcp-census --veri veri/ornek say" in out
    assert "Çıkış kodları" in out
    assert "usage:" not in out and "positional arguments" not in out
    for komut in ("indir", "say", "rapor", "karsilastir", "seri"):
        assert komut in out


@pytest.mark.parametrize("komut", ["indir", "say", "rapor", "karsilastir", "seri"])
def test_her_komutun_yardimi_ornek_ve_veri_seceneği_tasir(capsys, komut):
    kod, out, _ = _calistir([komut, "--help"], capsys)
    assert kod == 0
    assert "örnek: mcp-census" in out
    assert "--veri" in out


# --- eksik dosya: bir sonraki adımı söyler -------------------------------------

def test_veri_klasoru_yoksa_ornek_yolunu_gosterir(tmp_path: Path, capsys):
    kod, _, err = _calistir(["--veri", str(tmp_path / "yok"), "rapor"], capsys)
    assert kod == 2
    assert err.startswith("hata: ")
    assert "klasörü yok" in err
    assert "depo kökünde" in err
    assert "--veri veri/ornek rapor" in err


def test_say_kayit_yoksa_ornek_yolunu_ve_suresini_gosterir(tmp_path: Path, capsys):
    kod, _, err = _calistir(["--veri", str(tmp_path / "yok"), "say"], capsys)
    assert kod == 2
    assert "Önce `mcp-census indir`" in err
    assert "~15 dk" in err
    assert "--veri veri/ornek say" in err


def test_sayim_yok_ama_kayit_var_yalniz_say_der(tmp_path: Path, capsys):
    (tmp_path / "kayitlar.jsonl").write_text("", encoding="utf-8")
    kod, _, err = _calistir(["--veri", str(tmp_path), "rapor"], capsys)
    assert kod == 2
    assert "Önce `mcp-census say`" in err
    assert "klasörü yok" not in err


def test_ag_hatasinda_agsiz_komutlar_hatirlatilir(tmp_path: Path, monkeypatch, capsys):
    def patla(*a, **k):
        raise fetch.RegistryHatasi("http://x/v0/servers -> 3 denemede alınamadı")
    monkeypatch.setattr(fetch, "indir", patla)
    kod, _, err = _calistir(["--veri", str(tmp_path), "indir", "--sessiz"], capsys)
    assert kod == 2
    assert err.startswith("hata: http://x")
    assert "say, rapor, karsilastir, seri" in err
    assert not any(tmp_path.iterdir()), "başarısız indirme dosya bırakmamalı"


# --- rapor: ölçülmeyen değer soru işaretiyle değil açıkça yazılır -----------------

def test_ornek_raporunda_zaman_ve_kaynak_belirtilmemisse_soru_isareti_yok(capsys):
    _, out, _ = _calistir(["rapor", "--veri", str(KOK / "veri" / "ornek")], capsys)
    zaman = next(l for l in out.splitlines() if l.startswith("zaman"))
    assert zaman.split(None, 1)[1] == "belirtilmemiş"


# --- README'deki komutlar gerçekten ayrışıyor -----------------------------------

def _readme_komutlari() -> list[list[str]]:
    metin = (KOK / "README.md").read_text(encoding="utf-8")
    komutlar = []
    for blok in re.findall(r"```(?:bash|console)\n(.*?)```", metin, re.S):
        for satir in blok.splitlines():
            satir = re.sub(r"\s+#.*$", "", satir.strip())
            satir = re.sub(r"^\$\s+", "", satir)
            m = re.match(r"^(?:uv run )?mcp-census (.*)$", satir)
            if m:
                komutlar.append(shlex.split(m.group(1)))
    return komutlar


def test_readme_komutlari_var():
    assert len(_readme_komutlari()) >= 8


@pytest.mark.parametrize("argv", _readme_komutlari(), ids=lambda a: " ".join(a))
def test_readme_komutu_argumanlari_gecerli(argv):
    """README'de yazan her `mcp-census ...` satırı ayrıştırıcıdan geçer (çalıştırılmaz)."""
    # ~ ve yer tutucular yolu değiştirmez; yalnızca sözdizimi sınanıyor.
    try:
        cli.kur().parse_args(argv)
    except SystemExit as e:
        assert e.code == 0, f"{argv} ayrıştırılamadı"  # --help / --version çıkış 0 verir


# --- süzgeçli (latest) indirme sürüm ölçütlerini bozar, seriye girmez ---------------

def _latest_veri(tmp_path: Path) -> Path:
    from tests.test_cli import kayit
    d = tmp_path / "v"
    fetch.jsonl_yaz([kayit("a/b"), kayit("c/d")], d / "kayitlar.jsonl")
    fetch.manifest_yaz({"kaynak": "sahte", "indirme_zamani_utc": "2026-01-01T00:00:00Z",
                        "icerik_ozeti": "x", "tam_mi": True, "suzgec": {"version": "latest"}},
                       d / "manifest.json")
    return d


def test_rapor_suzgecli_indirmede_surum_olcutlerini_uyarir(tmp_path: Path, capsys):
    d = _latest_veri(tmp_path)
    assert cli.main(["--veri", str(d), "say"]) == 0
    capsys.readouterr()
    kod, out, _ = _calistir(["--veri", str(d), "rapor"], capsys)
    assert kod == 0
    assert "süzgeçle indirildi (version=latest)" in out
    assert "tek_surumlu_sunucu" in out.split("SAYILAR")[0]


def test_seri_suzgecli_indirmeyi_reddeder(tmp_path: Path, capsys):
    d = _latest_veri(tmp_path)
    assert cli.main(["--veri", str(d), "say"]) == 0
    capsys.readouterr()
    kod, _, err = _calistir(["--veri", str(d), "seri"], capsys)
    assert kod == 2
    assert "süzgeçli indirme" in err and "version=latest" in err
    assert not (d / "zaman-serisi.csv").exists()


# --- README görseli elle çizilmiş: sayıları veri/sayim.json'la tutmalı ----------

def _tr(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def test_okunacak_kod_svg_sayimla_tutarli():
    import json
    sayim = json.loads((KOK / "veri" / "sayim.json").read_text(encoding="utf-8"))
    b = {x["ad"]: x["deger"] for x in sayim["bulgular"]}
    toplam = b["ayri_sunucu_adi"]
    svg = (KOK / "assets" / "okunacak-kod.svg").read_text(encoding="utf-8")
    for ad in ("ayri_sunucu_adi", "deposuz_sunucu", "sadece_uzak_sunucu", "ne_paket_ne_uc"):
        assert _tr(b[ad]) in svg, f"SVG'de {ad} = {_tr(b[ad])} yok"
    dag = sayim["dagilimlar"]["depo_barindiricisi"]
    assert _tr(dag["github.com"]) in svg and str(dag["gitlab.com"]) in svg
    # çubuk genişlikleri: 640 px = tüm sunucular
    genislikler = [int(w) for w in re.findall(r'<rect x="0" y="0" width="(\d+)" height="20" rx="3" fill="#(?!1c1c24)', svg)]
    beklenen = [b["deposuz_sunucu"], b["sadece_uzak_sunucu"], b["ne_paket_ne_uc"]]
    assert len(genislikler) == 3
    for g, v in zip(genislikler, beklenen):
        assert abs(g - 640 * v / toplam) < 1.0, (g, v)


def test_veri_dosyalari_lf_ile_kilitli():
    """Windows'ta autocrlf `say` çıktısını CRLF yapıp `git status`i kirletiyordu."""
    ga = (KOK / ".gitattributes").read_text(encoding="utf-8")
    for desen in ("veri/**/*.json", "veri/**/*.jsonl", "veri/**/*.csv"):
        assert re.search(re.escape(desen) + r"\s+text eol=lf", ga), desen
