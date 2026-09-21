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
        },
        "en_cok_surum_yayinlayan": [
            {"ad": a, "surum_sayisi": c} for a, c in en_cok_surumlu
        ],
    }


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
