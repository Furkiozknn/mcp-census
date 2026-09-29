# Denetim: mcp-census (30 Eylül 2026)

Yenilemeden önce `master` (0.2.0, `16a8f9b`) üzerinde, bu makinede (Windows 11, Python 3.12 venv ve uv'nin 3.14'ü, uv 0.12.5, Git Bash) ölçüldü. Ölçülmeyen bir şey yazılmadı. Ham çıktılar depo dışında: `kanit/mcp-census/{once,sonra}/` (aynı 25 komut, iki sürüme karşı: `olc.py`; kurulum süreleri: `kurulum.py`).

## Temiz ortamda kurulum ve ilk sonuç

Her satır boş bir klasörde, boş bir uv önbelleğiyle koşuldu.

| Yol | Süre | Sonuç |
|---|---|---|
| `uvx --from git+https://github.com/Furkiozknn/mcp-census mcp-census --version` (boş önbellek, üç koşu) | 10,1 s, 10,2 s, 10,0 s | `mcp-census 0.2.0` |
| aynısı, önbellek sıcak | 2,7 s | aynı |
| `python -m venv` + `pip install git+...` | 19,6 s | `mcp-census 0.2.0` |
| `git clone --depth 1` + `uv run mcp-census rapor` (boş uv önbelleği; README'nin ilk komutu) | 5,8 s | 71 satır rapor, çıkış 0 |
| `uv sync --locked --group dev` (klon, README "Kurulum") | 3,1 s | çıkış 0 |
| `uv run pytest` | 1,7 s (pytest) | 104 geçti (önce), 148 geçti (sonra) |
| `indir --azami-sayfa 2` (ağ, README "30 saniyede dene") | 2,7 s | 200 satır, `TAM DEĞİL` uyarısı, çıkış 0 |
| `indir --surum latest` (ağ, tam) | 320,96 s (künyeden) | 37.477 kayıt, 375 sayfa |

"Tek komut, bir dakikada ilk sonuç" tutuyor: klon + ilk rapor 5,8 s. `uv run` ilk koşuda geliştirme grubunu (pytest, pygments, 7 paket) de kurar; çalışma zamanı bağımlılığı yine yok. README "uv sync ... yalnızca paketin kendisi" diyordu, düzeltildi. D: sürücüsündeki klonda uv, önbellek başka sürücüde olduğu için "Failed to hardlink" uyarısı basıyor; bu uv'nin uyarısı, aracın değil.

## README komutları

| Komut | Sonuç |
|---|---|
| `uv run mcp-census rapor` | çalıştı, hazır 16 Eylül sayımı, ağ yok |
| `uv run mcp-census --veri veri/ornek say` | çalıştı. **Windows'ta `git status` temiz kalmıyordu** (aşağıda) |
| `uv run mcp-census --veri veri/ornek rapor` | çalıştı |
| `--veri /tmp/deneme indir --azami-sayfa 2` | çalıştı; Windows'ta `/tmp` yok, `deneme` yazıldı |
| `uv tool install git+...` + `mcp-census --version` | çalıştı (`uvx` ile aynı yol); depo dışında `rapor` hazır sayımı bulamıyor |
| `karsilastir veri/kayitlar.jsonl veri/kayitlar-latest.jsonl` | ham dosyalar depoda yok (bilerek); önce `indir` gerekir. README bunu söylüyor |
| `indir --surum latest` | çalıştı, 5 dk 21 sn |
| PyPI "henüz yayında değil" | doğru: `pypi.org/pypi/mcp-census/json` 404 |

Sayılar: "104 test" → koşudan 104 (uyuştu). README'deki her sayı (105.038, 32.318, 31.972, %23,0, 18.183, 425, 24.841, 38, 3,25 sürüm/sunucu, medyan 1, 1.177) `veri/sayim.json` ve `manifest.json`'dan geliyor; `~15 dk, 1051 sayfa` künyeden (902,7 s, 1051 sayfa), `karsilastir` örneğindeki 32.321 `veri/manifest-latest.json`'dan (04:24 UTC, 15 dk sonra). `assets/okunacak-kod.svg` elle çizilmiş ama çubuk genişlikleri (147, 360, 8 px) ve sayılar `sayim.json`'la tutuyor; artık bir test bunu kilitliyor.

## Hata mesajları ve `--help`

Çıkış kodları hep doğruydu (kullanım/dosya/ağ hatası 2, kayıp 1, başarı 0; bozuk JSON, izin yok, bozuk `sayim.json` yığın izi değil `hata: …`). Sorun sözlerdeydi:

| Girdi | Önce | Sorun |
|---|---|---|
| `mcp-census` (komutsuz), `mcp-census nope`, `karsilastir x`, `--azami-sayfa 0` | `usage: … error: the following arguments are required: komut`, `invalid choice`, `unrecognized arguments` | Araç Türkçe konuşuyor, kullanım hataları İngilizce; diğer hatalardan (`hata: …`) farklı biçim; ne yazılacağı yok |
| `mcp-census rapor --veri veri/ornek` | `unrecognized arguments: --veri veri/ornek` | **Hata.** README "bütün komutlar `--veri` ile çalışır" diyor ama yalnızca komuttan önce kabul ediliyordu; en olası yazım yanlış |
| `--veri yok rapor` (ya da araç kurulup depo dışında `rapor`) | `hata: yok\sayim.json yok. Önce mcp-census say.` | `uv tool install` ile gelen biri `say` denediğinde bu kez `kayitlar.jsonl yok` alır ve hazır sayımın, örnek verinin depoda olduğunu hiçbir yerde öğrenmez |
| `--veri yok say` | `… Önce mcp-census indir.` | `indir`in ~15 dk sürdüğü ve örnek veri yolu söylenmiyor |
| ağ yok | `… 3 denemede alınamadı: …` | ağsız çalışan komutlar hatırlatılmıyor (~11 s beklettikten sonra) |
| `--help` | açıklama + çıkış kodları, İngilizce başlıklar (`positional arguments`, `options`) | örnek yok, `karsilastir` argümanları (`eski`, `yeni`) açıklamasız, alt komut yardımında örnek yok, `--veri` alt komut yardımında görünmüyor |
| `rapor` (örnek veri) | `kaynak veri/kayitlar.jsonl'den ornek`, `zaman ?` | ölçülmemiş değer `?` ile yazılıyor |
| okunamayan dosya (`icacls /deny`) | `hata: kilitli\kayitlar.jsonl: Permission denied` | doğru, tek satır; değiştirilmedi |
| bozuk giriş satırı | `hata: bozuk\kayitlar.jsonl:2 okunamadı: …` | doğru, satır numarası var; değiştirilmedi |

Önce/sonra metinleri: `kanit/mcp-census/once/komutlar.txt`, `sonra/komutlar.txt`.

## Veri bulguları (ölçüm dürüstlüğü)

- **Bayat başlık sayısı.** Depodaki sayım 16 Eylül 2026. 29 Eylül 22:16 UTC'de `indir --surum latest` 37.477 sunucu verdi (32.321 → 37.477, %16); oranlar yerinde (`repository` yok %23,0 → %24,2; yalnızca uzak uç %56,3 → %56,8). README'ye "Veri tazeliği" bölümü ve "anlık sayı için kullanmayın" satırı eklendi; başlık sayıları **değiştirilmedi** (bunlar 16 Eylül tam indirmesinden, o tarihle etiketli). Ham `latest` dosyası (35 MB) depoya konmadı; künye ve sayım `kanit/mcp-census/sonra/taze-latest-2026-09-29/`.
- **Süzgeçli veri seriyi bozabiliyordu.** `indir --surum latest` `tam_mi: true` künyesi yazar; `say` ondan `kayit_satiri` = sunucu sayısı ve `tek_surumlu_sunucu` %100 üretir (sürüm satırı yok). `seri` bunu kabul ederdi. Bir aylık koşu yanlışlıkla `--surum latest` ile alınsaydı seride "sürüm başına 3,25 satır" bir ay 1,00'a düşerdi. Artık `seri` reddediyor, `rapor` uyarıyor (test var).
- **Windows'ta `git status` temiz kalmıyordu.** `core.autocrlf=true` ile checkout `veri/**` dosyalarını CRLF yapıyor, `say` LF yazıyor; `git diff --exit-code` 0 dönse de `git status` `M` gösteriyor ve README'nin "bayt bayt aynı" iddiası Windows'ta bayt düzeyinde tutmuyordu. `.gitattributes` (`veri/** eol=lf`) eklendi.
- `veri/ornek/manifest.json` zaman damgası taşımıyor (`zaman ?`): örnek, tam indirmeden seçilmiş 500 satır; artık `belirtilmemiş` yazıyor, uydurulan bir zaman yok.

## README bulguları

- İlk ekran: banner + 15 sn "sesli" reel (`docs/reel/reel.gif`) + `assets/demo.gif` + 5 rozet + İngilizce katlanır bölüm; ilk komut "30 saniyede dene" bölümünde, tek cümle tanım yoktu (başlık iki italik satırdı).
- `docs/reel/reel.{gif,mp4}` ("15 saniyelik tanıtım videosu, sesli") ve `assets/demo.gif` ("gerçek çıktı, ağ olmadan"): **üreticileri depoda yok**, yeniden üretilemedi. README'den ve depodan çıkarıldı (git geçmişinde duruyor). Yerine `scripts/demo-uret.py` ile gerçek çıktıdan üretilen demo geldi.
- `assets/banner.svg` profil deposundaki üreticiden ("edit banners.json there, not this file"), GitHub mavisi paleti; bu depoda değiştirilmedi.
- Test sayısı üç yerde (rozet, `pytest # N test`, `project-meta.json`) ve CI bunu kilitliyor; üçü de 148.

## Testler ve CI

Önce: 104 test, hepsi geçti (Python 3.14 ve 3.12'de). CI: `ci.yml` (3.11–3.14 matrisi, paket, örnek yol), `sayim.yml` (aylık), `yayinla.yml`; `master`'daki son koşular yeşil. Sonra: 148 test; yerelde 3.11, 3.12, 3.13 ve 3.14'te geçti; CI durumu için bkz. PR.

## Günlük "Ekosistem denetimi" (#19, profil deposu)

Bu depoya ait açık bulgular: `project-meta.json` testleri ↔ `meta-source.json` (104 ↔ 55; şimdi 148 ↔ 55) ve "v0.1.0 etiketi atılmış ama PyPI'da 0.1.0 yok". İkisi de Furki'nin kararını bekliyor (`/meta` birleşmiş içeriği geri alır; PyPI yayını onay kapısında) — **kapatılmadı**. `project-meta.json`'da yalnızca gerçekten değişen alanlar (test sayısı, medya yolları) işlendi.

## Çözülmeyenler

- PyPI'da yayın yok (onay kapısı); `uv tool install git+...` tek yol.
- `karsilastir` README örneği ham `veri/kayitlar.jsonl` ister; ham veri depoda bilerek durmuyor (aylık 105 bin satır). Örnek çıktı README'de gerçek koşudan.
- Depo `description`'ı ve `meta-source.json` bayat olabilir; dokunulmadı.
- `banner.svg` FRK-OS değil (profil üreticisi).
