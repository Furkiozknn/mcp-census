# Katki Rehberi -- mcp-census

Takildigin yerde issue acmaktan cekinme. **"Bu rehber su noktada
anlasilmiyor" da gecerli bir issue'dur.**

## 1. Gelistirme ortami

Tek gereken [uv](https://pypi.org/project/uv/) ve Python 3.11+.
Calisma zamani bagimliligi yok; `uv sync` yalnizca pytest'i kurar.

```
git clone https://github.com/Furkiozknn/mcp-census.git
cd mcp-census
uv sync --locked --group dev    # CI de tam olarak bunu calistiriyor
uv run pytest                   # hicbir test aga cikmaz
```

Ag olmadan uctan uca denemek icin depodaki 500 kayitlik ornek:

```
uv run mcp-census --veri veri/ornek say
uv run mcp-census --veri veri/ornek rapor
git diff --exit-code veri/ornek/sayim.json   # say deterministik; fark cikmamali
```

## 2. Bu depoya ozgu kurallar

- **Calisma zamani bagimliligi eklenmez.** Bir olcum aracinin kurulumu bir
  tedarik zinciri sorusu olmamali. Yalnizca standart kutuphane.
- **Her sayi tanimini tasir.** Yeni bir olcut `analyze.sayim()` icinde bir
  `Bulgu` olarak eklenir: deger, tanim, payda. Tanimsiz sayi yok.
- **Zaman serisinin sutunlari degismez.** `SERI_SUTUNLARI` sirasini
  degistirmek eski satirlari okunamaz yapar; yeni sutun yalnizca SONA eklenir
  ve bunu kilitleyen test bilerek guncellenir.
- **Testler aga cikmaz.** `fetch` fonksiyonlari bir `getirici` alir; CLI
  testleri `fetch._istek`'i yamalar.
- **Hata duzeltiyorsan once hatayi yakalayan testi yaz**, eski kodda
  kirildigini gor, sonra duzelt.

## 3. PR

Dal adi ne yaptigini soylesin (`fix/bos-manifest`, `feat/yeni-olcut`).
Commit mesaji **neden**i anlatsin; ne yapildigi diff'te zaten gorunuyor.
PR sablonundaki "Nasil dogrulandi?" bolumune calistirdigin komutu ve
ciktisini (kac test gecti) yaz.

Surum cikarmak sahibin isidir: `pyproject.toml`, `mcp_census/__init__.py` ve
`CHANGELOG.md` ayni surumu gostermeli; `Yayinla` is akisi etikette bunu
denetler.
