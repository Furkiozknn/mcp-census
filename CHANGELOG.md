# Değişiklik günlüğü

Biçim Keep a Changelog, sürümleme Semantic Versioning. Sayım verisindeki
değişiklikler (aylık `chore: aylik sayim` commit'leri) burada değil,
[`veri/zaman-serisi.csv`](veri/zaman-serisi.csv) içinde izlenir.

## [0.2.0] — 2026-09-25

### Eklendi

- **Zaman serisi.** `veri/zaman-serisi.csv` ve ayda bir çalışan `Sayim` iş
  akışı: indirir, sayar, önceki sayımla ölçüt ölçüt karşılaştırır, seriye bir
  satır ekler. Ölçülmeyen ölçüt boş kalır, sıfıra çevrilmez.
- **`mcp-census seri`** — tam bir sayımı seriye ekler, önceki sayımla farkını
  Markdown olarak basar (`--onceki`, `--ozet`). Daha önce iş akışının içinde
  test edilmeyen satır içi Python olan mantık artık paketin parçası ve testli.
- `mcp-census --version`.
- PyPI yayın iş akışı (`yayinla.yml`, Trusted Publishing; API anahtarı yok).
- CI: Python 3.11–3.14 matrisi, `uv sync --locked`, paket derleme +
  `twine check --strict` + tekerleğin temiz bir ortamda kurulup çağrılması,
  README'deki örnek-veri yolunun çalıştırılması.
- `SECURITY.md`, `CONTRIBUTING.md`, PR ve hata bildirimi şablonları,
  Dependabot (GitHub Actions + uv).

### Düzeltildi

- **Kısmi bir deneme zaman serisini bozabiliyordu.** `Sayim` iş akışı elle
  `azami_sayfa: 5` ile tetiklendiğinde 500 satırlık sayımı `master`'a commit
  ediyor ve seriye "registry %99 küçüldü" satırı ekliyordu. Artık kısmi
  koşu hiçbir şey commit etmez; `mcp-census seri` de kısmi ya da künyesiz
  sayımı reddeder (çıkış 2).
- **İş akışı girdisi kabuğa metin olarak gömülüyordu**
  (`${{ github.event.inputs.azami_sayfa }}` bir `run:` betiğinin içinde).
  Artık ortam değişkeninden okunuyor ve tamsayı olduğu doğrulanıyor.
- **`--surum` dosyayı veri klasörünün dışına yazdırabiliyordu** (değer
  `kayitlar-<surum>.jsonl` adına giriyor; `../../x` gibi değerler artık
  reddediliyor).
- **`--taban` `file://` ve `ftp://` adreslerini açıyordu.** Yalnızca
  `http(s)` kabul ediliyor.
- Registry yanıtına üst sınır (32 MiB, açılmış hâliyle): gzip bombası ya da
  başka bir sunucuya çevrilmiş `--taban` belleği sınırsız dolduramaz.
- Bozuk ya da eksik girdi artık Python yığın izi yerine tek satırlık
  `hata: …` ve çıkış 2 veriyor: olmayan dosya (`karsilastir`), bozuk JSONL
  satırı ya da nesne olmayan satır (`say`), bozuk `manifest.json`, şekli
  bozuk `sayim.json` (`rapor`, `seri`), yazılamayan `--yaz` yolu, nesne
  olmayan registry yanıtı.
- `--azami-sayfa 0`, `--sayfa-boyu 0` ağa çıkmadan reddediliyor.
- Paket meta verisi `Metadata-Version 2.4` olarak üretiliyor: hatchling 1.32
  varsayılanı olan 2.5'i `twine check` (7.0) reddediyordu, yani yayın iş
  akışı ilk koşusunda kırılacaktı. Lisans SPDX (`MIT`) olarak yazılıyor.

## [0.1.0] — 2026-09-22

İlk sürüm: resmî MCP Registry'nin yeniden üretilebilir sayımı — ham veri,
onu üreten kod ve her sayının tanımı bir arada.

- `mcp-census indir` — registry'nin tamamını çeker (`kayitlar.jsonl` +
  `manifest.json`); `--surum latest` ile sunucu başına tek satır.
- `mcp-census say` / `rapor` — sayım ve okunur rapor, ağ yok.
- `mcp-census karsilastir` — iki indirmeyi karşılaştırır; kayıp gördüğünde
  çıkış 1.
- İlk ölçüm (16 Eylül 2026): 105.038 satır, 32.318 ayrı sunucu, 31.972 aktif.

[0.2.0]: https://github.com/Furkiozknn/mcp-census/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Furkiozknn/mcp-census/releases/tag/v0.1.0
