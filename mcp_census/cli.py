# -*- coding: utf-8 -*-
"""mcp-census komut satırı.

Üç komut, üç ayrı adım — ve ayrı olmaları bilinçli:

    mcp-census indir    registry'yi çeker, ham satırları + künyeyi yazar
    mcp-census say      ham satırlardan sayımı üretir (ağ yok)
    mcp-census rapor    sayımı okunur metne çevirir (ağ yok)
    mcp-census seri     tam bir sayımı zaman serisine ekler (ağ yok)

`say` ve `rapor` ağa çıkmadığı için, elinizdeki `kayitlar.jsonl` ile
sonuçlar her seferinde aynı çıkar. Bir sayıya itiraz eden kişi aynı dosyayı
alıp aynı komutu çalıştırabilir; tartışma "sende farklı çıkmış olabilir"
noktasına düşmez.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
from pathlib import Path

from . import __version__, analyze, fetch

VARSAYILAN_VERI = Path("veri")

# `--surum` değeri çıktı dosyasının adına giriyor (kayitlar-<surum>.jsonl).
# Yol ayırıcısı ya da `..` içeren bir değer dosyayı veri klasörünün dışına
# yazdırabilirdi; yalnızca düz bir ad kabul ediliyor.
_SURUM_DESENI = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,63}")


def _surum_turu(deger: str) -> str:
    if not _SURUM_DESENI.fullmatch(deger) or ".." in deger:
        raise argparse.ArgumentTypeError(
            f"geçersiz sürüm süzgeci {deger!r}: harf/rakam ile başlayan, yalnızca "
            "harf, rakam, '.', '_', '+', '-' içeren bir değer olmalı (ör. latest)"
        )
    return deger


def _pozitif_tamsayi(deger: str) -> int:
    try:
        n = int(deger)
    except ValueError:
        raise argparse.ArgumentTypeError(f"tamsayı değil: {deger!r}") from None
    if n < 1:
        raise argparse.ArgumentTypeError(f"en az 1 olmalı: {n}")
    return n


def _taban_turu(deger: str) -> str:
    try:
        return fetch.taban_dogrula(deger)
    except fetch.RegistryHatasi as e:
        raise argparse.ArgumentTypeError(str(e)) from None


class _GirdiHatasi(Exception):
    """Kullanıcıya tek satır olarak gösterilecek, çıkış 2 veren hata."""


def _cikti_utf8() -> None:
    """Windows'ta cp1254 stdout'u Unicode'da patlatır; baştan sabitle."""
    for akim in (sys.stdout, sys.stderr):
        try:
            akim.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _sayim_yok(veri: Path, sayim_yolu: Path) -> str:
    """`rapor` / `seri` sayım dosyasını bulamadı: durumuna göre doğru yolu söyle."""
    ilk = f"hata: {sayim_yolu} yok. Önce `mcp-census say`."
    if (veri / "kayitlar.jsonl").exists():
        return ilk
    if not veri.exists():
        neden = f"'{veri}' klasörü yok; komutu depo kökünde mi çalıştırdınız?"
    else:
        neden = f"'{veri}' içinde ne sayim.json ne kayitlar.jsonl var."
    return (f"{ilk}\n"
            f"      {neden}\n"
            f"      Örnek veriyle: `mcp-census --veri veri/ornek rapor`\n"
            f"      Kendi sayımınız: `mcp-census indir`, sonra `say`.")


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
        print(f"hata: {e}\n"
              f"      Ağ gerektirmeyen komutlar: say, rapor, karsilastir, seri "
              f"(örnek: `mcp-census --veri veri/ornek rapor`).", file=sys.stderr)
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
        print(f"hata: {kayit_yolu} yok. Önce `mcp-census indir` (ağa çıkar, tam indirme ~15 dk).\n"
              f"      Beklemeden denemek için depodaki 500 kayıtlık örnek: "
              f"`mcp-census --veri veri/ornek say`", file=sys.stderr)
        return 2
    kayitlar = fetch.jsonl_oku(kayit_yolu)
    sonuc = analyze.sayim(kayitlar)

    manifest_yolu = veri / "manifest.json"
    if manifest_yolu.exists():
        try:
            manifest = json.loads(manifest_yolu.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise _GirdiHatasi(f"{manifest_yolu} geçerli JSON değil: {e}") from e
        if not isinstance(manifest, dict):
            raise _GirdiHatasi(f"{manifest_yolu} bir JSON nesnesi değil")
        sonuc["kaynak_manifest"] = manifest

    analyze.sayimi_yaz(sonuc, veri / "sayim.json")
    print(f"sayım yazıldı -> {veri / 'sayim.json'}")
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
        print(_sayim_yok(veri, sayim_yolu), file=sys.stderr)
        return 2
    s = analyze.sayim_oku(sayim_yolu)

    if a.json:
        print(json.dumps(s, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    satirlar: list[str] = []
    ek = satirlar.append
    ek("MCP REGISTRY SAYIMI")
    ek("=" * 56)
    m = s.get("kaynak_manifest") or {}
    if m:
        ek(f"kaynak     {m.get('kaynak', 'belirtilmemiş')}")
        ek(f"zaman      {m.get('indirme_zamani_utc', 'belirtilmemiş')}")
        ek(f"özet       {str(m.get('icerik_ozeti', 'belirtilmemiş'))[:32]}…")
        if not m.get("tam_mi", True):
            ek("DİKKAT     bu veri kümesi kısmi (manifest: tam_mi=false) - "
               "sayılar tüm registry'yi temsil etmiyor")
        if m.get("suzgec"):
            ek("DİKKAT     veri süzgeçle indirildi (%s): sunucu başına tek satır var, "
               "kayit_satiri / isLatest_isaretli_satir / tek_surumlu_sunucu ve"
               % ",".join("%s=%s" % kv for kv in sorted(m["suzgec"].items())))
            ek("           'en çok sürüm yayınlayan' sürüm dağılımını ölçmez")
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
    for baslik, d in (s.get("dagilimlar") or {}).items():
        if not d:
            continue
        ek(f"DAĞILIM — {baslik}")
        for k, v in d.items():
            ek(f"  {k:<26} {v:>9}")
        ek("")
    ek("EN ÇOK SÜRÜM YAYINLAYAN")
    for x in (s.get("en_cok_surum_yayinlayan") or [])[:10]:
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
    for yol in (a.eski, a.yeni):
        if not Path(yol).is_file():
            raise _GirdiHatasi(f"{yol} yok ya da bir dosya değil")
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


def komut_seri(a: argparse.Namespace) -> int:
    veri = Path(a.veri)
    sayim_yolu = veri / "sayim.json"
    if not sayim_yolu.exists():
        print(_sayim_yok(veri, sayim_yolu), file=sys.stderr)
        return 2
    yeni = analyze.sayim_oku(sayim_yolu)
    uygun, neden = analyze.seriye_uygun_mu(yeni)
    if not uygun:
        print(f"hata: {neden}", file=sys.stderr)
        return 2

    fark: dict = {"degisti_mi": True, "olcutler": []}
    if a.onceki:
        fark = analyze.sayim_farki(analyze.sayim_oku(Path(a.onceki)), yeni)

    seri_yolu = Path(a.seri) if a.seri else veri / "zaman-serisi.csv"
    eklendi = analyze.seriye_ekle(seri_yolu, analyze.seri_satiri(yeni))
    ozet = analyze.seri_ozeti(fark, yeni, eklendi)
    print(ozet, end="")
    if a.ozet:
        with io.open(a.ozet, "a", encoding="utf-8", newline="\n") as f:
            f.write(ozet)
    return 0


# argparse'in yardım başlıkları ve iç mesajları İngilizce gelir. Anahtar
# bulunamazsa (Python sürümleri arasında metin değişebilir) İngilizcesi kalır;
# hiçbir şey bozulmaz, yalnızca çevrilmez.
_TR = {
    "usage: ": "kullanım: ",
    "positional arguments": "komutlar ve argümanlar",
    "options": "seçenekler",
    "show this help message and exit": "bu yardımı göster ve çık",
    "show program's version number and exit": "sürümü göster ve çık",
}

_HATA_CEVIRI = (
    (re.compile(r"^the following arguments are required: (.*)$"), r"eksik argüman: \1"),
    (re.compile(r"^unrecognized arguments: (.*)$"), r"tanınmayan argüman: \1"),
    (re.compile(r"^argument komut: invalid choice: (.*?) \(choose from (.*)\)$"),
     r"bilinmeyen komut \1 (komutlar: \2)"),
    (re.compile(r"^argument (\S+): invalid choice: (.*?) \(choose from (.*)\)$"),
     r"\1: geçersiz değer \2 (seçenekler: \3)"),
    (re.compile(r"^argument (\S+): expected one argument$"), r"\1 bir değer bekliyor"),
    (re.compile(r"^argument (\S+): (.*)$"), r"\1: \2"),
)


def _cevir(metin: str) -> str:
    return _TR.get(metin, metin)


class _Ayristirici(argparse.ArgumentParser):
    """Kullanım hatasını uygulamanın diğer hatalarıyla aynı biçimde basar:
    `hata: …` tek satır, ardından ne yazılacağı. Çıkış kodu 2 (argparse ile aynı)."""

    def error(self, message: str):
        for desen, yerine in _HATA_CEVIRI:
            yeni_mesaj, n = desen.subn(yerine, message)
            if n:
                message = yeni_mesaj
                break
        print(f"hata: {message}", file=sys.stderr)
        print(f"      yardım: `{self.prog} --help`", file=sys.stderr)
        self.exit(2)


_ORNEKLER = """hızlı başlangıç (ağ yok; depo kökünde):
  mcp-census rapor                         depodaki son sayım (veri/sayim.json)
  mcp-census --veri veri/ornek say         500 kayıtlık örnekten sayımı baştan üret
  mcp-census indir --surum latest          registry'nin bugünkü hâli (ağ, ~5 dk)

Yalnızca `indir` ağa çıkar. `--veri KLASÖR` komuttan önce de sonra da yazılabilir.
Çıkış kodları: 0 başarılı · 1 karsilastir kayıp kayıt buldu · 2 girdi/ağ/dosya hatası.
"""


def kur() -> argparse.ArgumentParser:
    """Komut satırı ayrıştırıcısı; testler README'deki komutları bununla süzer."""
    argparse._ = _cevir  # ponytail: özel ad; sürüm değişirse çeviri düşer, davranış bozulmaz
    p = _Ayristirici(
        prog="mcp-census",
        description="Resmî MCP Registry'nin yeniden üretilebilir sayımı: kaç sunucu var, "
                    "kaçının okunacak kodu var, hangi sayı hangi tanımla üretildi.",
        epilog=_ORNEKLER,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--version", action="version",
                   version=f"%(prog)s {__version__}")
    p.add_argument("--veri", default=str(VARSAYILAN_VERI), metavar="KLASÖR",
                   help="veri klasörü (varsayılan: veri)")
    # `--veri` komuttan sonra da yazılabilsin: `mcp-census rapor --veri veri/ornek`.
    # SUPPRESS: komutun kendi varsayılanı üstteki değeri ezmesin.
    ortak = argparse.ArgumentParser(add_help=False)
    ortak.add_argument("--veri", default=argparse.SUPPRESS, metavar="KLASÖR",
                       help="veri klasörü (varsayılan: veri)")
    alt = p.add_subparsers(dest="komut", required=True, metavar="komut",
                           parser_class=_Ayristirici)

    def komut(ad, yardim, ornek):
        return alt.add_parser(ad, help=yardim, description=yardim, parents=[ortak],
                              epilog="örnek: " + ornek)

    i = komut("indir", "registry'yi indir (ağa çıkan tek komut)",
              "mcp-census indir --surum latest    # ~5 dk, kayitlar-latest.jsonl")
    i.add_argument("--taban", type=_taban_turu, default=fetch.VARSAYILAN_TABAN,
                   help="registry adresi, yalnızca http(s) (varsayılan: %(default)s)")
    i.add_argument("--sayfa-boyu", type=_pozitif_tamsayi, default=fetch.SAYFA_BOYU,
                   help="sayfa başına kayıt (varsayılan: %(default)s)")
    i.add_argument("--azami-sayfa", type=_pozitif_tamsayi, default=None,
                   help="test için tavan; verilirse sayım TAM DEĞİL sayılır")
    i.add_argument("--surum", type=_surum_turu, default=None, metavar="SUZGEC",
                   help="registry'nin version süzgeci; `latest` sunucu başına "
                        "tek satır döndürür. Çıktı kayitlar-latest.jsonl olur.")
    i.add_argument("--sessiz", action="store_true", help="ilerleme satırlarını basma")
    i.set_defaults(fn=komut_indir)

    s = komut("say", "indirilmiş satırlardan sayımı üret (ağ yok)",
              "mcp-census --veri veri/ornek say")
    s.set_defaults(fn=komut_say)

    r = komut("rapor", "sayımı okunur metne çevir (ağ yok)",
              "mcp-census rapor | head -n 22")
    r.add_argument("--json", action="store_true", help="makine okunur çıktı")
    r.add_argument("--yaz", default=None, help="metni bu dosyaya da yaz")
    r.set_defaults(fn=komut_rapor)

    k = komut("karsilastir", "iki indirmeyi sunucu adı düzeyinde karşılaştır (ağ yok)",
              "mcp-census karsilastir veri/kayitlar.jsonl veri/kayitlar-latest.jsonl")
    k.add_argument("eski", help="önceki indirme (.jsonl)")
    k.add_argument("yeni", help="sonraki indirme (.jsonl); eskide olup yenide olmayan varsa çıkış 1")
    k.add_argument("--json", action="store_true", help="makine okunur çıktı")
    k.set_defaults(fn=komut_karsilastir)

    z = komut("seri", "tam bir sayımı veri/zaman-serisi.csv'ye ekle (ağ yok)",
              "mcp-census seri --onceki eski-sayim.json")
    z.add_argument("--onceki", default=None, metavar="SAYIM_JSON",
                   help="karşılaştırılacak önceki sayim.json")
    z.add_argument("--seri", default=None, metavar="CSV",
                   help="seri dosyası (varsayılan: <veri>/zaman-serisi.csv)")
    z.add_argument("--ozet", default=None, metavar="DOSYA",
                   help="Markdown özeti bu dosyanın sonuna da ekle "
                        "(ör. $GITHUB_STEP_SUMMARY)")
    z.set_defaults(fn=komut_seri)
    return p


def main(argv: list[str] | None = None) -> int:
    _cikti_utf8()
    a = kur().parse_args(argv)
    try:
        return a.fn(a)
    except (_GirdiHatasi, fetch.RegistryHatasi, analyze.SayimHatasi) as e:
        print(f"hata: {e}", file=sys.stderr)
        return 2
    except BrokenPipeError:
        # Çıktıyı okuyan taraf kapandı (ör. `mcp-census rapor | head`). Bu bir
        # hata değil; Python'un çıkışta ikinci kez patlamaması için stdout
        # /dev/null'a yönlendiriliyor. 141 = 128 + SIGPIPE, kabuk geleneği.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return 141
    except OSError as e:
        yer = f"{e.filename}: " if e.filename else ""
        print(f"hata: {yer}{e.strerror or e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
