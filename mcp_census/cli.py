# -*- coding: utf-8 -*-
"""mcp-census komut satırı.

Üç komut, üç ayrı adım — ve ayrı olmaları bilinçli:

    mcp-census indir    registry'yi çeker, ham satırları + künyeyi yazar
    mcp-census say      ham satırlardan sayımı üretir (ağ yok)
    mcp-census rapor    sayımı okunur metne çevirir (ağ yok)

`say` ve `rapor` ağa çıkmadığı için, elinizdeki `kayitlar.jsonl` ile
sonuçlar her seferinde aynı çıkar. Bir sayıya itiraz eden kişi aynı dosyayı
alıp aynı komutu çalıştırabilir; tartışma "sende farklı çıkmış olabilir"
noktasına düşmez.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

from . import analyze, fetch

VARSAYILAN_VERI = Path("veri")


def _cikti_utf8() -> None:
    """Windows'ta cp1254 stdout'u Unicode'da patlatır; baştan sabitle."""
    for akim in (sys.stdout, sys.stderr):
        try:
            akim.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def komut_indir(a: argparse.Namespace) -> int:
    veri = Path(a.veri)

    def ilerleme(sayfa: int, toplam: int) -> None:
        if sayfa % 10 == 0 or sayfa == 1:
            print(f"  sayfa {sayfa}, {toplam} kayıt", file=sys.stderr, flush=True)

    try:
        sonuc = fetch.indir(
            taban=a.taban,
            limit=a.sayfa_boyu,
            azami_sayfa=a.azami_sayfa,
            ilerleme=None if a.sessiz else ilerleme,
            suzgec={"version": a.surum} if a.surum else None,
        )
    except fetch.RegistryHatasi as e:
        print(f"hata: {e}", file=sys.stderr)
        return 2

    ek = f"-{a.surum}" if a.surum else ""
    fetch.jsonl_yaz(sonuc.kayitlar, veri / f"kayitlar{ek}.jsonl")
    fetch.manifest_yaz(sonuc.manifest, veri / f"manifest{ek}.json")
    m = sonuc.manifest
    print(
        f"{m['kayit_sayisi']} kayıt, {m['sayfa_sayisi']} sayfa, "
        f"{m['suren_saniye']} sn -> {veri}/"
    )
    print(f"içerik özeti: {m['icerik_ozeti']}")
    if not m["tam_mi"]:
        print("UYARI: --azami-sayfa verildi, bu sayım TAM DEĞİL.", file=sys.stderr)
    return 0


def komut_say(a: argparse.Namespace) -> int:
    veri = Path(a.veri)
    kayit_yolu = veri / "kayitlar.jsonl"
    if not kayit_yolu.exists():
        print(f"hata: {kayit_yolu} yok. Önce `mcp-census indir`.", file=sys.stderr)
        return 2
    kayitlar = fetch.jsonl_oku(kayit_yolu)
    sonuc = analyze.sayim(kayitlar)

    manifest_yolu = veri / "manifest.json"
    if manifest_yolu.exists():
        sonuc["kaynak_manifest"] = json.loads(manifest_yolu.read_text(encoding="utf-8"))

    analyze.sayimi_yaz(sonuc, veri / "sayim.json")
    print(f"sayım yazıldı -> {veri}/sayim.json")
    return 0


def _satir(b: dict) -> str:
    deger = f"{b['deger']:,}".replace(",", ".")
    if b.get("yuzde") is not None:
        return f"  {b['ad']:<26} {deger:>9}   %{b['yuzde']}"
    return f"  {b['ad']:<26} {deger:>9}"


def komut_rapor(a: argparse.Namespace) -> int:
    veri = Path(a.veri)
    sayim_yolu = veri / "sayim.json"
    if not sayim_yolu.exists():
        print(f"hata: {sayim_yolu} yok. Önce `mcp-census say`.", file=sys.stderr)
        return 2
    s = json.loads(sayim_yolu.read_text(encoding="utf-8"))

    if a.json:
        print(json.dumps(s, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    satirlar: list[str] = []
    ek = satirlar.append
    ek("MCP REGISTRY SAYIMI")
    ek("=" * 56)
    m = s.get("kaynak_manifest") or {}
    if m:
        ek(f"kaynak     {m.get('kaynak', '?')}")
        ek(f"zaman      {m.get('indirme_zamani_utc', '?')}")
        ek(f"özet       {str(m.get('icerik_ozeti', '?'))[:32]}…")
        if not m.get("tam_mi", True):
            ek("DİKKAT     bu veri kümesi kısmi (manifest: tam_mi=false) - "
               "sayılar tüm registry'yi temsil etmiyor")
    ek("")
    ek("SAYILAR")
    for b in s["bulgular"]:
        ek(_satir(b))
    ek("")
    ek("TANIMLAR")
    for b in s["bulgular"]:
        ek(f"  {b['ad']}")
        ek(f"      {b['tanim']}")
    ek("")
    for baslik, d in s["dagilimlar"].items():
        if not d:
            continue
        ek(f"DAĞILIM — {baslik}")
        for k, v in d.items():
            ek(f"  {k:<26} {v:>9}")
        ek("")
    ek("EN ÇOK SÜRÜM YAYINLAYAN")
    for x in s["en_cok_surum_yayinlayan"][:10]:
        ek(f"  {x['ad']:<44} {x['surum_sayisi']:>5} sürüm")

    metin = "\n".join(satirlar)
    print(metin)
    if a.yaz:
        yol = Path(a.yaz)
        yol.parent.mkdir(parents=True, exist_ok=True)
        with io.open(yol, "w", encoding="utf-8", newline="\n") as f:
            f.write(metin + "\n")
        print(f"\n-> {yol}", file=sys.stderr)
    return 0


def komut_karsilastir(a: argparse.Namespace) -> int:
    eski = fetch.jsonl_oku(Path(a.eski))
    yeni = fetch.jsonl_oku(Path(a.yeni))
    sonuc = analyze.karsilastir(eski, yeni)
    if a.json:
        print(json.dumps(sonuc, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"eski   {sonuc['eski_sunucu']:>7} sunucu")
        print(f"yeni   {sonuc['yeni_sunucu']:>7} sunucu")
        print(f"eklenen {sonuc['eklenen_sayisi']:>6}   kaybolan {sonuc['kaybolan_sayisi']}")
        print()
        print(sonuc["yorum"])
        if sonuc["eklenen"]:
            print()
            print("eklenenler (ilk 50):")
            for x in sonuc["eklenen"]:
                print("  +", x)
        if sonuc["kaybolan"]:
            print()
            print("kaybolanlar (ilk 50):")
            for x in sonuc["kaybolan"]:
                print("  -", x)
    # Kayıp varsa çıkış 1: CI'da iki indirmeyi karşılaştıran bir iş bunu yakalasın.
    return 0 if sonuc["yalnizca_ekleme_mi"] else 1


def main(argv: list[str] | None = None) -> int:
    _cikti_utf8()
    p = argparse.ArgumentParser(
        prog="mcp-census",
        description="Resmî MCP Registry'nin yeniden üretilebilir sayımı.",
    )
    p.add_argument("--veri", default=str(VARSAYILAN_VERI),
                   help="veri klasörü (varsayılan: veri)")
    alt = p.add_subparsers(dest="komut", required=True)

    i = alt.add_parser("indir", help="registry'yi indir")
    i.add_argument("--taban", default=fetch.VARSAYILAN_TABAN)
    i.add_argument("--sayfa-boyu", type=int, default=fetch.SAYFA_BOYU)
    i.add_argument("--azami-sayfa", type=int, default=None,
                   help="test için tavan; verilirse sayım TAM DEĞİL sayılır")
    i.add_argument("--surum", default=None, metavar="SUZGEC",
                   help="registry'nin version süzgeci; `latest` sunucu başına "
                        "tek satır döndürür. Çıktı kayitlar-latest.jsonl olur.")
    i.add_argument("--sessiz", action="store_true")
    i.set_defaults(fn=komut_indir)

    s = alt.add_parser("say", help="indirilmiş satırlardan sayımı üret (ağ yok)")
    s.set_defaults(fn=komut_say)

    r = alt.add_parser("rapor", help="sayımı okunur metne çevir (ağ yok)")
    r.add_argument("--json", action="store_true")
    r.add_argument("--yaz", default=None, help="metni bu dosyaya da yaz")
    r.set_defaults(fn=komut_rapor)

    k = alt.add_parser("karsilastir",
                       help="iki indirmeyi sunucu adı düzeyinde karşılaştır (ağ yok)")
    k.add_argument("eski")
    k.add_argument("yeni")
    k.add_argument("--json", action="store_true")
    k.set_defaults(fn=komut_karsilastir)

    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
