# -*- coding: utf-8 -*-
"""Resmî MCP Registry'yi sayfa sayfa indirir ve olduğu gibi diske yazar.

Tasarım kuralı: bu modül **yorumlamaz**. Registry ne döndürdüyse onu
`kayitlar.jsonl` içine satır satır yazar, yanına da indirmenin kendisini
tarif eden bir `manifest.json` koyar. Analiz ayrı bir adımdır (`analyze.py`),
çünkü bir sayıyı tartışmak isteyen kişinin ham veriye ulaşabilmesi gerekir.

Neden bu ayrım önemli: ekosistem hakkında dolaşan sayıların çoğu
("kayıt defterinde N sunucu var") tek bir satıcının tek seferlik taramasından
geliyor ve yeniden üretilemiyor. Burada indirme ile yorum ayrıldığı için
aynı `kayitlar.jsonl` üzerinde başka biri farklı bir analiz yazabilir, ya da
aynı analizi yeniden koşturup sayının hâlâ tuttuğunu görebilir.

Yalnızca standart kütüphane kullanır.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterator

VARSAYILAN_TABAN = "https://registry.modelcontextprotocol.io"
SAYFA_BOYU = 100
KULLANICI_AJANI = "mcp-census (+https://github.com/Furkiozknn/mcp-census)"

# Registry bir sayfayı döndüremezse kaç kez denenecek. Geçici 5xx ve kopan
# bağlantılar için; 4xx'te denemeye devam etmek anlamsız, hemen yükselir.
DENEME = 3
DENEME_BEKLEME = 1.5


class RegistryHatasi(RuntimeError):
    """Registry'den beklenen şekilde veri alınamadı."""


@dataclass
class Sayfa:
    """Tek bir registry sayfası."""

    kayitlar: list[dict]
    sonraki_imlec: str | None


@dataclass
class IndirmeSonucu:
    """Bir indirmenin tamamı: satırlar + onu tarif eden künye."""

    kayitlar: list[dict]
    manifest: dict = field(default_factory=dict)


def _istek(url: str, zaman_asimi: float) -> bytes:
    istek = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "User-Agent": KULLANICI_AJANI,
        },
    )
    with urllib.request.urlopen(istek, timeout=zaman_asimi) as yanit:
        ham = yanit.read()
        if yanit.headers.get("Content-Encoding") == "gzip":
            ham = gzip.decompress(ham)
        return ham


def sayfa_getir(
    imlec: str | None = None,
    *,
    taban: str = VARSAYILAN_TABAN,
    limit: int = SAYFA_BOYU,
    zaman_asimi: float = 30.0,
    getirici: Callable[[str, float], bytes] | None = None,
    suzgec: dict[str, str] | None = None,
) -> Sayfa:
    """Tek sayfa indirir.

    `getirici` testlerin ağa çıkmadan sahte yanıt verebilmesi için var;
    üretimde `None` bırakılır ve `urllib` kullanılır.

    `suzgec` registry'nin kendi sorgu parametreleri için — özellikle
    `{"version": "latest"}`. Bu süzgeç sayımın merkezindeki karşılaştırmayı
    mümkün kılıyor: süzgeçsiz çağrı her sürüm için bir satır döndürür,
    `version=latest` ise sunucu başına bir satır. İkisinin farkı, ekosistem
    hakkında dolaşan "N sunucu var" cümlesinin neden yanıltıcı olduğudur.
    """
    al = getirici or _istek
    url = f"{taban}/v0/servers?limit={int(limit)}"
    for anahtar, deger in sorted((suzgec or {}).items()):
        url += f"&{urllib.parse.quote(anahtar)}={urllib.parse.quote(str(deger))}"
    if imlec:
        url += f"&cursor={urllib.parse.quote(imlec, safe='')}"

    son_hata: Exception | None = None
    for deneme in range(DENEME):
        try:
            ham = al(url, zaman_asimi)
            break
        except urllib.error.HTTPError as e:
            # 4xx kalıcıdır: imleç bozuk ya da uç değişmiş. Tekrar denemek
            # aynı cevabı alır, sadece zaman kaybettirir.
            if 400 <= e.code < 500:
                raise RegistryHatasi(f"{url} -> HTTP {e.code}") from e
            son_hata = e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            son_hata = e
        if deneme < DENEME - 1:
            time.sleep(DENEME_BEKLEME * (deneme + 1))
    else:
        raise RegistryHatasi(f"{url} -> {DENEME} denemede alınamadı: {son_hata}")

    try:
        govde = json.loads(ham.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise RegistryHatasi(f"{url} -> yanıt JSON değil: {e}") from e

    kayitlar = govde.get("servers")
    if not isinstance(kayitlar, list):
        raise RegistryHatasi(f"{url} -> yanıtta 'servers' listesi yok")

    ustveri = govde.get("metadata") or {}
    return Sayfa(kayitlar=kayitlar, sonraki_imlec=ustveri.get("nextCursor") or None)


def sayfalar(
    *,
    taban: str = VARSAYILAN_TABAN,
    limit: int = SAYFA_BOYU,
    azami_sayfa: int | None = None,
    zaman_asimi: float = 30.0,
    getirici: Callable[[str, float], bytes] | None = None,
    suzgec: dict[str, str] | None = None,
) -> Iterator[Sayfa]:
    """Registry'yi imleç bitene kadar sayfa sayfa dolaşır.

    İki güvenlik kemeri var, ikisi de gerçek bir tehlikeye karşı:
    `azami_sayfa` çağıranın koyduğu tavan, `gorulen_imlecler` ise registry
    aynı imleci ikinci kez verirse (sunucu tarafı hata) sonsuz döngüyü keser.
    """
    imlec: str | None = None
    gorulen_imlecler: set[str] = set()
    sayac = 0
    while True:
        sayfa = sayfa_getir(
            imlec, taban=taban, limit=limit, zaman_asimi=zaman_asimi,
            getirici=getirici, suzgec=suzgec,
        )
        yield sayfa
        sayac += 1
        if azami_sayfa is not None and sayac >= azami_sayfa:
            return
        if not sayfa.sonraki_imlec:
            return
        if sayfa.sonraki_imlec in gorulen_imlecler:
            raise RegistryHatasi(
                f"imleç tekrar etti ({sayfa.sonraki_imlec!r}); döngüyü kesiyorum"
            )
        gorulen_imlecler.add(sayfa.sonraki_imlec)
        imlec = sayfa.sonraki_imlec


def indir(
    *,
    taban: str = VARSAYILAN_TABAN,
    limit: int = SAYFA_BOYU,
    azami_sayfa: int | None = None,
    zaman_asimi: float = 30.0,
    getirici: Callable[[str, float], bytes] | None = None,
    ilerleme: Callable[[int, int], None] | None = None,
    suzgec: dict[str, str] | None = None,
) -> IndirmeSonucu:
    """Registry'nin tamamını indirir ve künyesiyle birlikte döndürür."""
    baslangic = time.time()
    kayitlar: list[dict] = []
    sayfa_sayisi = 0
    for sayfa in sayfalar(
        taban=taban,
        limit=limit,
        azami_sayfa=azami_sayfa,
        zaman_asimi=zaman_asimi,
        getirici=getirici,
        suzgec=suzgec,
    ):
        kayitlar.extend(sayfa.kayitlar)
        sayfa_sayisi += 1
        if ilerleme:
            ilerleme(sayfa_sayisi, len(kayitlar))

    manifest = {
        "arac": "mcp-census",
        "manifest_surumu": 1,
        "kaynak": taban,
        "indirme_zamani_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(baslangic)),
        "suren_saniye": round(time.time() - baslangic, 2),
        "sayfa_sayisi": sayfa_sayisi,
        "sayfa_boyu": limit,
        "suzgec": dict(sorted((suzgec or {}).items())),
        "kayit_sayisi": len(kayitlar),
        "tam_mi": azami_sayfa is None,
        "icerik_ozeti": kayitlarin_ozeti(kayitlar),
    }
    return IndirmeSonucu(kayitlar=kayitlar, manifest=manifest)


def kayitlarin_ozeti(kayitlar: list[dict]) -> str:
    """İndirilen satırların içerik özeti (sha256).

    Aynı özeti üreten iki indirme aynı veriyi görmüştür. Bir sayı tartışmalı
    hale geldiğinde "hangi anlık görüntüye bakıyoruz" sorusunun cevabı budur.
    """
    h = hashlib.sha256()
    for kayit in kayitlar:
        h.update(json.dumps(kayit, sort_keys=True, ensure_ascii=False).encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def jsonl_yaz(kayitlar: list[dict], yol: Path) -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    with io.open(yol, "w", encoding="utf-8", newline="\n") as f:
        for kayit in kayitlar:
            f.write(json.dumps(kayit, ensure_ascii=False, sort_keys=True))
            f.write("\n")


def jsonl_oku(yol: Path) -> list[dict]:
    kayitlar: list[dict] = []
    with io.open(yol, encoding="utf-8") as f:
        for satir_no, satir in enumerate(f, 1):
            satir = satir.strip()
            if not satir:
                continue
            try:
                kayitlar.append(json.loads(satir))
            except json.JSONDecodeError as e:
                raise RegistryHatasi(f"{yol}:{satir_no} okunamadı: {e}") from e
    return kayitlar


def manifest_yaz(manifest: dict, yol: Path) -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    with io.open(yol, "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
