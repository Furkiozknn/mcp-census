# -*- coding: utf-8 -*-
"""İndirilmiş registry satırlarını sayıma çevirir.

Her sayı bir `Bulgu`dur ve üç şey taşır: değer, o değerin hangi tanımdan
çıktığı, ve hangi satır kümesine bakıldığı. Bunu taşımayan sayı üretmiyoruz,
çünkü bu deponun tamamı şu gözlemin üzerine kurulu: ekosistem hakkında
dolaşan rakamların çoğu tanımını söylemiyor.

Somut örnek: "kayıt defterinde N sunucu var" cümlesi üç farklı şeyi
kastedebilir ve üçü de farklı sayı verir — kaç satır döndü, kaç ayrı sunucu
adı var, kaç tanesi hâlâ yayında. Fark küçük değil; sürüm başına bir satır
döndüğü için satır sayısı ayrı sunucu sayısının katı olabiliyor.
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable

RESMI_META = "io.modelcontextprotocol.registry/official"


class SayimHatasi(ValueError):
    """Bir sayım dosyası okunamadı ya da beklenen şekilde değil."""


@dataclass(frozen=True)
class Bulgu:
    """Tek bir ölçüm: değeri, tanımı ve payda."""

    ad: str
    deger: float | int
    tanim: str
    payda: int | None = None

    @property
    def yuzde(self) -> float | None:
        if self.payda in (None, 0):
            return None
        return round(100.0 * self.deger / self.payda, 1)


def _sunucu(kayit: dict) -> dict:
    s = kayit.get("server")
    return s if isinstance(s, dict) else {}


def _resmi_meta(kayit: dict) -> dict:
    meta = kayit.get("_meta")
    if not isinstance(meta, dict):
        return {}
    r = meta.get(RESMI_META)
    return r if isinstance(r, dict) else {}


def ad(kayit: dict) -> str:
    return str(_sunucu(kayit).get("name") or "")


def surum(kayit: dict) -> str:
    return str(_sunucu(kayit).get("version") or "")


def durum(kayit: dict) -> str:
    return str(_resmi_meta(kayit).get("status") or "bilinmiyor")


def en_son_mu(kayit: dict) -> bool:
    return bool(_resmi_meta(kayit).get("isLatest"))


def depo_urlsi(kayit: dict) -> str | None:
    """Kaynak kodun adresi, varsa.

    Bu alan olmadan sunucu **denetlenemez**: okunacak kod yoktur. Sayımdaki
    en önemli ayrımlardan biri bu, çünkü "yıldızına değil koduna bak"
    tavsiyesi ancak ortada kod varsa işe yarar.
    """
    depo = _sunucu(kayit).get("repository")
    if isinstance(depo, dict):
        url = depo.get("url")
        return str(url) if url else None
    if isinstance(depo, str) and depo:
        return depo
    return None


def paketler(kayit: dict) -> list[dict]:
    p = _sunucu(kayit).get("packages")
    return [x for x in p if isinstance(x, dict)] if isinstance(p, list) else []


def uzak_uclar(kayit: dict) -> list[dict]:
    r = _sunucu(kayit).get("remotes")
    return [x for x in r if isinstance(x, dict)] if isinstance(r, list) else []


def sadece_uzak_mi(kayit: dict) -> bool:
    """Yalnızca uzak uç sunan kayıt: çalışan kod sizin makinenizde değil.

    mcp-vet'in kendi tehdit modelinde açıkça yazan kör nokta bu — uzak bir
    sunucuda okuyabildiğiniz kod, çalışan kod olmak zorunda değil. Kaç
    kaydın bu durumda olduğunu ölçmek, o kör noktanın büyüklüğünü ölçmektir.
    """
    return bool(uzak_uclar(kayit)) and not paketler(kayit)


def install_shape(kayit: dict) -> str:
    """How a server can be used: what it offers to install or connect to.

    The four values partition the latest-version set, so they always add up
    to `en_son_surumler`: `yalnizca_paket` (a package you run yourself),
    `yalnizca_uzak` (only a remote endpoint), `paket_ve_uzak` (both) and
    `hicbiri` (neither - nothing to install).
    """
    has_package, has_remote = bool(paketler(kayit)), bool(uzak_uclar(kayit))
    if has_package and has_remote:
        return "paket_ve_uzak"
    if has_package:
        return "yalnizca_paket"
    if has_remote:
        return "yalnizca_uzak"
    return "hicbiri"


def namespace(kayit: dict) -> str:
    """The part of `server.name` before the first '/', e.g. `io.github.acme`."""
    name = ad(kayit)
    return name.split("/", 1)[0] if "/" in name else ""


def namespace_kind(kayit: dict) -> str:
    """Which authority vouched for the namespace.

    The registry proves a name in one of two ways: a GitHub login
    (`io.github.<user>`) or control of a domain (reverse DNS such as
    `com.example`). The share of each says how much of the registry rests on
    a GitHub account rather than a domain someone owns.
    """
    ns = namespace(kayit)
    if ns == "io.github" or ns.startswith("io.github."):
        return "io.github"
    if "." in ns:
        return "alan_adi"
    return "diger"


TOP_NAMESPACES = 15


def en_son_kayitlar(kayitlar: Iterable[dict]) -> list[dict]:
    """Sunucu adı başına tek kayıt.

    Tercih sırası: `isLatest` işaretli olan; yoksa o adın en son görülen
    satırı. Registry sıralamayı sürüm sırasına göre verdiği için "en son
    görülen" makul bir yedek, ama bu bir varsayım ve raporda öyle yazılır.
    """
    secili: dict[str, dict] = {}
    for kayit in kayitlar:
        a = ad(kayit)
        if not a:
            continue
        onceki = secili.get(a)
        if onceki is None:
            secili[a] = kayit
        elif en_son_mu(kayit):
            secili[a] = kayit
        elif not en_son_mu(onceki):
            secili[a] = kayit
    return list(secili.values())


def _sorted_counts(counter: Counter) -> list[tuple[str, int]]:
    """Most common first, ties by key, so the output is byte-stable."""
    return sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))


def sayim(kayitlar: list[dict]) -> dict[str, Any]:
    """Bütün sayımı üretir."""
    toplam_satir = len(kayitlar)
    adlar = [ad(k) for k in kayitlar if ad(k)]
    ayri_ad = len(set(adlar))
    en_sonlar = en_son_kayitlar(kayitlar)
    n = len(en_sonlar)

    durumlar = Counter(durum(k) for k in en_sonlar)
    aktifler = [k for k in en_sonlar if durum(k) == "active"]

    isLatest_isaretli = sum(1 for k in kayitlar if en_son_mu(k))

    deposuz = [k for k in en_sonlar if not depo_urlsi(k)]
    sadece_uzak = [k for k in en_sonlar if sadece_uzak_mi(k)]
    paketsiz_ucsuz = [
        k for k in en_sonlar if not paketler(k) and not uzak_uclar(k)
    ]

    paket_turleri: Counter[str] = Counter()
    for k in en_sonlar:
        for p in paketler(k):
            paket_turleri[str(p.get("registryType") or "bilinmiyor")] += 1

    uc_turleri: Counter[str] = Counter()
    for k in en_sonlar:
        for r in uzak_uclar(k):
            uc_turleri[str(r.get("type") or "bilinmiyor")] += 1

    # Per server rather than per package: a server shipping two npm
    # packages counts once here, twice in `paket_turu`.
    paket_turu_sunucu: Counter[str] = Counter()
    uc_turu_sunucu: Counter[str] = Counter()
    for k in en_sonlar:
        for t in {str(p.get("registryType") or "bilinmiyor") for p in paketler(k)}:
            paket_turu_sunucu[t] += 1
        for t in {str(r.get("type") or "bilinmiyor") for r in uzak_uclar(k)}:
            uc_turu_sunucu[t] += 1

    kurulum = Counter(install_shape(k) for k in en_sonlar)
    ad_alani_turleri = Counter(namespace_kind(k) for k in en_sonlar)
    ad_alanlari = Counter(namespace(k) for k in en_sonlar if namespace(k))

    surum_sayisi = Counter(adlar)
    tek_surumluler = sum(1 for _, c in surum_sayisi.items() if c == 1)
    en_cok_surumlu = surum_sayisi.most_common(15)

    aciklamasiz = [
        k for k in en_sonlar
        if len(str(_sunucu(k).get("description") or "").strip()) < 20
    ]

    barindirici: Counter[str] = Counter()
    for k in en_sonlar:
        url = depo_urlsi(k)
        if not url:
            continue
        parca = url.split("//", 1)[-1].split("/", 1)[0].lower()
        barindirici[parca or "bilinmiyor"] += 1

    bulgular = [
        Bulgu("kayit_satiri", toplam_satir,
              "registry'nin /v0/servers ucundan dönen satır sayısı; "
              "sürüm başına bir satır"),
        Bulgu("ayri_sunucu_adi", ayri_ad,
              "satırlardaki ayrı `server.name` değeri sayısı", toplam_satir),
        Bulgu("en_son_surumler", n,
              "sunucu adı başına tek kayda indirgenmiş küme"),
        Bulgu("isLatest_isaretli_satir", isLatest_isaretli,
              "`_meta[...].isLatest` alanı true olan satır sayısı", toplam_satir),
        Bulgu("aktif_sunucu", len(aktifler),
              "en son sürümünün durumu `active` olan sunucu", n),
        Bulgu("deposuz_sunucu", len(deposuz),
              "`server.repository` alanı olmayan sunucu — okunacak kaynak yok", n),
        Bulgu("sadece_uzak_sunucu", len(sadece_uzak),
              "yalnızca uzak uç sunan, indirilebilir paketi olmayan sunucu", n),
        Bulgu("ne_paket_ne_uc", len(paketsiz_ucsuz),
              "ne paket ne uzak uç bildiren sunucu — kurulacak bir şey yok", n),
        Bulgu("kisa_aciklama", len(aciklamasiz),
              "açıklaması 20 karakterden kısa sunucu", n),
        Bulgu("tek_surumlu_sunucu", tek_surumluler,
              "registry'de yalnızca tek sürümü olan sunucu", ayri_ad),
    ]

    return {
        "bulgular": [asdict(b) | {"yuzde": b.yuzde} for b in bulgular],
        "dagilimlar": {
            "durum": dict(durumlar.most_common()),
            "paket_turu": dict(paket_turleri.most_common()),
            "uzak_uc_turu": dict(uc_turleri.most_common()),
            "depo_barindiricisi": dict(barindirici.most_common(10)),
            "kurulum_bicimi": {k: kurulum.get(k, 0) for k in
                               ("yalnizca_paket", "yalnizca_uzak", "paket_ve_uzak", "hicbiri")},
            "paket_turu_sunucu": dict(_sorted_counts(paket_turu_sunucu)),
            "uzak_uc_turu_sunucu": dict(_sorted_counts(uc_turu_sunucu)),
            "ad_alani_turu": {k: ad_alani_turleri.get(k, 0) for k in ("io.github", "alan_adi", "diger")},
            "en_buyuk_ad_alanlari": dict(_sorted_counts(ad_alanlari)[:TOP_NAMESPACES]),
        },
        "en_cok_surum_yayinlayan": [
            {"ad": a, "surum_sayisi": c} for a, c in en_cok_surumlu
        ],
    }


def sayim_oku(yol: Path) -> dict[str, Any]:
    """`sayim.json` dosyasını okur ve şeklini doğrular.

    `rapor` ve `seri` bu dosyanın içine körlemesine bakıyor. Elle düzenlenmiş
    ya da yarım kalmış bir dosya bir `KeyError` yığını yerine hangi alanın
    eksik olduğunu söyleyen tek satırlık bir hata vermeli.
    """
    yol = Path(yol)
    try:
        s = json.loads(yol.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SayimHatasi(f"{yol} geçerli JSON değil: {e}") from e
    if not isinstance(s, dict):
        raise SayimHatasi(f"{yol} bir JSON nesnesi değil")
    bulgular = s.get("bulgular")
    if not isinstance(bulgular, list) or not all(
        isinstance(b, dict) and {"ad", "deger", "tanim"} <= set(b) for b in bulgular
    ):
        raise SayimHatasi(
            f"{yol} bir sayım dosyası değil: 'bulgular' listesi yok ya da "
            "öğelerinde ad/deger/tanim eksik"
        )
    for anahtar, tur in (("dagilimlar", dict), ("en_cok_surum_yayinlayan", list)):
        if not isinstance(s.get(anahtar, tur()), tur):
            raise SayimHatasi(f"{yol}: '{anahtar}' beklenen türde değil")
    if not all(isinstance(d, dict) for d in (s.get("dagilimlar") or {}).values()):
        raise SayimHatasi(f"{yol}: 'dagilimlar' altındaki her dağılım bir nesne olmalı")
    return s


def sayimi_yaz(sonuc: dict, yol: Path) -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    with open(yol, "w", encoding="utf-8", newline="\n") as f:
        json.dump(sonuc, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def karsilastir(eski: list[dict], yeni: list[dict]) -> dict[str, Any]:
    """İki indirmeyi sunucu adı düzeyinde karşılaştırır.

    Bunun asıl işi bir sayımı savunmak. Aynı registry'yi on beş dakika arayla
    iki kez indirdiğinizde sayı değişir — ve değişmesi normaldir. Önemli olan
    değişimin **açıklanabilir** olması: yalnızca ekleme mi oldu, yoksa
    kayıtlar kayboldu mu? Kaybolma varsa ya registry bir şey sildi ya da
    indirme eksik kaldı, ve ikisi çok farklı şeyler.
    """
    a = {ad(k) for k in eski if ad(k)}
    b = {ad(k) for k in yeni if ad(k)}
    eklenen = sorted(b - a)
    kaybolan = sorted(a - b)
    return {
        "eski_sunucu": len(a),
        "yeni_sunucu": len(b),
        "eklenen_sayisi": len(eklenen),
        "kaybolan_sayisi": len(kaybolan),
        "yalnizca_ekleme_mi": not kaybolan,
        "eklenen": eklenen[:50],
        "kaybolan": kaybolan[:50],
        "yorum": (
            "Fark yalnızca eklemeden ibaret; iki indirme arasında registry "
            "büyümüş. Sayım tutarlı."
            if not kaybolan
            else "Kayıp kayıt var. Ya registry sildi ya indirme eksik kaldı - "
                 "ikisi farklı şeyler, manifest sayfa sayısına bakın."
        ),
    }


# --------------------------------------------------------------------------
# zaman serisi
# --------------------------------------------------------------------------
#
# `karsilastir` iki İNDİRMEYİ sunucu adı düzeyinde karşılaştırıyor ve bir
# sayımı savunmak için var. Aşağıdakiler farklı bir soruyu cevaplıyor: aynı
# ölçüm aylar içinde nereye gidiyor?
#
# Ham kayıtlar depoda durmuyor -- 105 bin satır, her indirmede yeniden. Ama
# `veri/sayim.json` duruyor, ve bir sayımın zaman içindeki seyri ham veriden
# bağımsız olarak anlamlı: "kaç sunucunun okunacak kodu yok" sorusunun cevabı
# artıyor mu, azalıyor mu? Tek bir sayı bunu söyleyemez.


def sayim_farki(eski: dict, yeni: dict) -> dict[str, Any]:
    """İki sayımı ölçüt ölçüt karşılaştırır.

    İkisinde de bulunmayan bir ölçüt sessizce atlanmıyor: yeni eklenen ölçüt
    ``yeni_olcutler``, kaybolan ``dusen_olcutler`` altında adıyla duruyor.
    Bir ölçütün adı değiştiğinde seri kopar, ve bunun görünmesi gerekir.
    """
    def indeks(s: dict) -> dict[str, Any]:
        return {b["ad"]: b for b in (s.get("bulgular") or [])}

    e, y = indeks(eski), indeks(yeni)
    ortak = sorted(set(e) & set(y))
    degisenler = []
    for ad in ortak:
        onceki, simdiki = e[ad].get("deger"), y[ad].get("deger")
        if not all(isinstance(x, (int, float)) and not isinstance(x, bool)
                   for x in (onceki, simdiki)):
            continue
        fark = simdiki - onceki
        degisenler.append({
            "ad": ad,
            "onceki": onceki,
            "simdiki": simdiki,
            "fark": fark,
            "yuzde": (round(100.0 * fark / onceki, 2) if onceki else None),
            "tanim": y[ad].get("tanim", ""),
        })

    hareketli = [d for d in degisenler if d["fark"] != 0]
    return {
        "eski_zaman": (eski.get("kaynak_manifest") or {}).get("indirme_zamani_utc"),
        "yeni_zaman": (yeni.get("kaynak_manifest") or {}).get("indirme_zamani_utc"),
        "olcutler": degisenler,
        "hareketli_sayisi": len(hareketli),
        "yeni_olcutler": sorted(set(y) - set(e)),
        "dusen_olcutler": sorted(set(e) - set(y)),
        "degisti_mi": bool(hareketli or (set(y) ^ set(e))),
    }


#: Zaman serisinin sütunları. Sıra sabit: bir CSV'nin sütun sırası değişirse
#: eski satırlar okunamaz hâle gelir, ve bu dosyanın tek amacı eski satırların
#: okunabilir kalması.
SERI_SUTUNLARI = (
    "indirme_zamani_utc",
    "kayit_satiri",
    "ayri_sunucu_adi",
    "aktif_sunucu",
    "deposuz_sunucu",
    "sadece_uzak_sunucu",
    "ne_paket_ne_uc",
    "kisa_aciklama",
    "tek_surumlu_sunucu",
    # Added 2026-10: breakdowns. New columns are only ever appended, so the
    # columns above keep their positions; rows written before a column existed
    # read it as empty ("not measured"), never as zero.
    "yalnizca_paket",
    "paket_ve_uzak",
    "npm_sunucu",
    "pypi_sunucu",
    "oci_sunucu",
    "mcpb_sunucu",
    "streamable_http_sunucu",
    "io_github_ad_alani",
    "alan_adi_ad_alani",
)

#: Series columns that come from a distribution rather than from a finding:
#: column -> (distribution, key). A key missing from a distribution that
#: exists is a real zero; a missing distribution leaves the cell empty.
SERI_DAGILIM_SUTUNLARI: dict[str, tuple[str, str]] = {
    "yalnizca_paket": ("kurulum_bicimi", "yalnizca_paket"),
    "paket_ve_uzak": ("kurulum_bicimi", "paket_ve_uzak"),
    "npm_sunucu": ("paket_turu_sunucu", "npm"),
    "pypi_sunucu": ("paket_turu_sunucu", "pypi"),
    "oci_sunucu": ("paket_turu_sunucu", "oci"),
    "mcpb_sunucu": ("paket_turu_sunucu", "mcpb"),
    "streamable_http_sunucu": ("uzak_uc_turu_sunucu", "streamable-http"),
    "io_github_ad_alani": ("ad_alani_turu", "io.github"),
    "alan_adi_ad_alani": ("ad_alani_turu", "alan_adi"),
}


def seri_satiri(sayim_sonucu: dict) -> dict[str, Any]:
    """Bir sayımdan zaman serisinin bir satırını çıkarır.

    Eksik bir ölçüt boş bırakılıyor, sıfıra çevrilmiyor: "o gün ölçülmedi" ile
    "o gün sıfırdı" aynı şey değil ve bir seride bu fark her şeydir.
    """
    bulgular = {b["ad"]: b.get("deger") for b in (sayim_sonucu.get("bulgular") or [])}
    satir: dict[str, Any] = {
        "indirme_zamani_utc": (sayim_sonucu.get("kaynak_manifest") or {}).get("indirme_zamani_utc", "")
    }
    dagilimlar = sayim_sonucu.get("dagilimlar") or {}
    for ad in SERI_SUTUNLARI[1:]:
        if ad in SERI_DAGILIM_SUTUNLARI:
            dagilim, anahtar = SERI_DAGILIM_SUTUNLARI[ad]
            d = dagilimlar.get(dagilim)
            satir[ad] = d.get(anahtar, 0) if isinstance(d, dict) else ""
        else:
            satir[ad] = bulgular.get(ad, "")
    return satir


def seriye_uygun_mu(sayim_sonucu: dict) -> tuple[bool, str]:
    """Bu sayım zaman serisine girebilir mi? (evet/hayır, neden)

    Seriye yalnızca **tam** bir indirmeden üretilmiş sayım girer. Kısmi bir
    indirme (`--azami-sayfa`) 500 satırlık bir sayım üretir; seriye girerse
    grafikte registry'nin bir ayda %99 küçüldüğü görünür. Künyesi olmayan bir
    sayımın tam olup olmadığı bilinemez, o da girmez.
    """
    km = sayim_sonucu.get("kaynak_manifest")
    if not isinstance(km, dict):
        return False, "sayımda kaynak_manifest yok; tam bir indirmeden geldiği bilinemiyor"
    if km.get("tam_mi") is not True:
        return False, "kısmi indirme (manifest: tam_mi != true); seriye eklenmez"
    if not km.get("indirme_zamani_utc"):
        return False, "manifestte indirme_zamani_utc yok"
    if km.get("suzgec"):
        # `--surum latest` sunucu başına tek satır getirir: kayit_satiri sunucu
        # sayısına eşitlenir, tek_surumlu_sunucu %100 çıkar. Aynı seriye girse
        # ay ay karşılaştırılamayan iki tür satır karışırdı.
        return False, ("süzgeçli indirme (manifest: suzgec=%s); sürüm sayısına bağlı "
                       "ölçütler bundan anlamlı çıkmaz, seriye eklenmez"
                       % ",".join("%s=%s" % kv for kv in sorted(km["suzgec"].items())))
    return True, ""


def seri_ozeti(fark: dict[str, Any], yeni: dict, eklendi: bool) -> str:
    """Bir aylık sayımın Markdown özeti (iş akışı özeti için)."""
    km = yeni.get("kaynak_manifest") or {}
    satirlar = ["### Sayim", ""]
    satirlar.append("Indirme: `%s`, %s satir, %s sayfa."
                    % (km.get("indirme_zamani_utc"), km.get("kayit_sayisi"), km.get("sayfa_sayisi")))
    satirlar.append("")
    if fark.get("olcutler"):
        satirlar += ["| olcut | onceki | simdiki | fark |", "| --- | ---: | ---: | ---: |"]
        for o in fark["olcutler"]:
            isaret = "+" if o["fark"] > 0 else ""
            satirlar.append("| `%s` | %s | %s | %s%s |"
                            % (o["ad"], o["onceki"], o["simdiki"], isaret, o["fark"]))
    for anahtar, baslik in (("yeni_olcutler", "Yeni olcut"), ("dusen_olcutler", "Dusen olcut")):
        if fark.get(anahtar):
            satirlar.append("")
            satirlar.append("%s: %s" % (baslik, ", ".join("`%s`" % x for x in fark[anahtar])))
    satirlar.append("")
    satirlar.append("Seriye satir eklendi: **%s**" % ("evet" if eklendi else "hayir, ayni damga zaten var"))
    return "\n".join(satirlar) + "\n"


def _seriyi_genislet(yol: Path, baslik: list[str], satirlar: list[dict[str, str]]) -> None:
    """Rewrite an older series file under the current header.

    Only an older header that is a prefix of `SERI_SUTUNLARI` is accepted:
    columns were appended, so every existing cell keeps its meaning and the
    new cells are empty. Any other header means the file is not one this
    version wrote, and rewriting it could move a number into the wrong
    column, so that is an error instead.
    """
    import csv

    if not baslik or baslik != list(SERI_SUTUNLARI[: len(baslik)]):
        raise SayimHatasi(
            f"{yol}: sütunlar {','.join(baslik) or '(boş)'} bu sürümün sütunlarının "
            "başı değil; dosya elle düzenlenmiş olabilir, yeniden yazılmadı"
        )
    with open(yol, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(SERI_SUTUNLARI), lineterminator="\n")
        w.writeheader()
        for r in satirlar:
            w.writerow({k: r.get(k, "") or "" for k in SERI_SUTUNLARI})


def seriye_ekle(yol: Path, satir: dict[str, Any]) -> bool:
    """Satırı CSV'ye ekler. Aynı zaman damgası zaten varsa hiçbir şey yapmaz.

    Dönen değer: satır gerçekten eklendi mi. İş akışı bunu commit edip
    etmeyeceğine karar vermek için kullanıyor.
    """
    import csv

    yol = Path(yol)
    damga = str(satir.get("indirme_zamani_utc") or "")
    if not damga:
        raise ValueError("zaman damgasi olmayan bir satir seriye eklenemez")

    var_olan: list[dict[str, str]] = []
    if yol.is_file():
        with open(yol, encoding="utf-8", newline="") as f:
            okuyucu = csv.DictReader(f)
            var_olan = list(okuyucu)
            baslik = list(okuyucu.fieldnames or [])
        if any(r.get("indirme_zamani_utc") == damga for r in var_olan):
            return False
        if baslik != list(SERI_SUTUNLARI):
            _seriyi_genislet(yol, baslik, var_olan)

    yol.parent.mkdir(parents=True, exist_ok=True)
    yeni = yol.is_file() is False
    with open(yol, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(SERI_SUTUNLARI), lineterminator="\n")
        if yeni:
            w.writeheader()
        w.writerow({k: satir.get(k, "") for k in SERI_SUTUNLARI})
    return True
