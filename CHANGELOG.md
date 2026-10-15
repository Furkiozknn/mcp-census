# Değişiklik günlüğü

Biçim Keep a Changelog, sürümleme Semantic Versioning. Sayım verisindeki
değişiklikler (aylık `chore: aylik sayim` commit'leri) burada değil,
[`veri/zaman-serisi.csv`](veri/zaman-serisi.csv) içinde izlenir.

## [Yayınlanmamış]

### Değişti

- **Hata mesajları Türkçe ve bir sonraki adımı söylüyor.** Kullanım hataları
  (`eksik argüman`, `bilinmeyen komut`, `tanınmayan argüman`) artık argparse'in
  İngilizce iskeleti yerine `hata: …` + `yardım: …` basıyor (çıkış kodu hâlâ 2).
  Depo dışında `rapor`/`say` ve ağ hatası, kullanıcıyı `--veri veri/ornek` ya da
  `indir` yoluna yönlendiriyor.
- `--help`: hızlı başlangıç örnekleri, her komutta örnek, `karsilastir`
  argümanlarının açıklaması.
- `rapor`: künyede olmayan alan `?` yerine `belirtilmemiş` yazıyor.

### Eklendi

- **`mcp-census disa-aktar`** (İngilizce takma ad `export`): en son sürüm
  kümesi, sunucu başına bir satır, CSV ya da JSON Lines
  (`mcp_census/export.py`). Sütunlar sabit, satırlar ada göre sıralı; alanlar
  `analyze.py`'nin tanımlarını kullanır, örnek veride toplamlar `say` ile
  birebir tutuyor. CSV'de formül gibi başlayan hücrelere `'` eklenir (CSV
  injection). Çıktı `.gitignore`'da.
- **Kırılımlar** (`say` → `dagilimlar`): `kurulum_bicimi` (en son sürüm
  kümesini dörde bölen kurulum biçimi), `paket_turu_sunucu` ve
  `uzak_uc_turu_sunucu` (paket/uç türü **sunucu başına bir kez**; mevcut
  `paket_turu` paket sayar), `ad_alani_turu` (`io.github` / `alan_adi` /
  `diger`) ve `en_buyuk_ad_alanlari` (ilk 15). Dokuz yeni zaman serisi sütunu
  sona eklendi; eski CSV ilk `seri`de yeni başlıkla yeniden yazılır, eski
  satırların yeni hücreleri boş kalır, tanınmayan başlık reddedilir.
  `veri/zaman-serisi.csv` genişletildi, `veri/ornek/sayim.json` yeniden üretildi.
- **`mcp-census gorsel`**: README görseli (`assets/okunacak-kod.svg`) artık
  `veri/sayim.json`'dan üretiliyor (`mcp_census/gorsel.py`, yerleşim elle
  çizilmiş özgünle bayt bayt aynı). `--denetle` yazmadan karşılaştırır,
  uyuşmazlıkta çıkış 1. Sebep: 1 Ekim 2026 aylık sayımı `sayim.json`'ı
  güncelledi ama elle çizilmiş görseli güncelleyemedi; `test_okunacak_kod_svg_sayimla_tutarli`
  o commit'ten beri `master`'da kırmızıydı (bot commit'i CI'ı tetiklemediği
  için görünmedi). Görsel 1 Ekim sayımıyla yeniden üretildi.
- `--veri KLASÖR` komuttan sonra da yazılabiliyor (`mcp-census rapor --veri veri/ornek`);
  önceden `tanınmayan argüman` hatası veriyordu.
- `rapor`, `--surum latest` ile indirilmiş (süzgeçli) veri için sürüm
  ölçütlerinin anlamsız olduğunu uyarıyor.
- `.gitattributes`: `veri/` altı LF (Windows'ta `core.autocrlf=true` iken `say`
  çıktısı `git status`i kirletiyordu).
- `scripts/demo-uret.py`, `scripts/demo-kayit.js`, `docs/demo/`: README demosu
  gerçek komut çıktısından üretiliyor. Üreticisi olmayan `docs/reel/` ve
  `assets/demo.gif` çıkarıldı (git geçmişinde duruyor).
- 44 test (`tests/test_ilk_kullanim.py`): mesajlar, `--veri` konumu, README'deki
  her komutun ayrıştırılması, elle çizilmiş SVG'nin sayımla tutarlılığı.

### Düzeltildi

- **Süzgeçli indirme zaman serisine girebiliyordu.** `indir --surum latest`
  `tam_mi: true` künyesi yazdığı için `seri` kabul ederdi; `kayit_satiri` ve
  `tek_surumlu_sunucu` sürüm satırı taşımayan veride anlamsızlaşır. `seri` artık
  künyesinde `suzgec` olan sayımı reddediyor.

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
