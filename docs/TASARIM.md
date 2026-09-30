# Tasarım: mcp-census ilk kullanım ve README yenilemesi (30 Eylül 2026)

## Hedef

Videodan ya da profilden gelen biri ilk dakikada şunu yapabilmeli: aracın ne yaptığını tek cümlede anlamak, tek komutla ilk sayımı görmek, yanlış bir komut yazarsa ya da depo dışında çalıştırırsa doğrusunu ekranda görmek, ve **sayının ne kadar taze olduğunu** okumak. Çekirdek davranış (sayım tanımları, künye, çıkış kodları, sıfır çalışma zamanı bağımlılığı, `say`/`rapor`ın ağa çıkmaması) değişmedi; sürüm numarası artmadı (0.2.0).

## Önce / sonra

| Konu | Önce | Sonra |
|---|---|---|
| README ilk ekranı | banner, "sesli" reel GIF, `demo.gif`, beş rozet, İngilizce katlanır bölüm; tek cümle tanım yok, ilk komut aşağıda | banner, tek cümle tanım, tek satırlık klon + ilk rapor (ölçülmüş 5,8 s), rozetler, 17 sn gerçek çıktılı terminal demosu, "kullanın / kullanmayın" tablosu |
| Demo | kaynağı depoda olmayan reel ve GIF | `scripts/demo-uret.py`: 5 komut klonda gerçekten koşulur, `docs/demo/komutlar.txt` kayıttır, sayfa o kaydı oynatır; `demo-kayit.js` mp4/gif alır |
| Veri tazeliği | yalnızca 16 Eylül tarihi; bugünkü durum yok | "Veri tazeliği" bölümü: 29 Eylül `latest` indirmesi 37.477 sunucu (+%16), oranlar yerinde; başlık sayıları 16 Eylül etiketli kaldı |
| Kullanım hatası | argparse İngilizcesi (`the following arguments are required`) | `hata: eksik argüman: yeni` + `yardım: mcp-census karsilastir --help` (çıkış hâlâ 2) |
| `--veri` konumu | yalnızca komuttan önce | komuttan önce de sonra da |
| Depo dışında `rapor`/`say` | `Önce mcp-census say/indir.` | aynı satır + klasör yok mu, örnek veri komutu, kendi sayımın yolu, `indir` süresi |
| Ağ hatası | tek satır | + "ağ gerektirmeyen komutlar: say, rapor, karsilastir, seri" |
| `--help` | açıklama + çıkış kodları | hızlı başlangıç örnekleri, her komutta örnek, argüman açıklamaları, Türkçe başlıklar |
| Süzgeçli (`latest`) veri | seriye girebilirdi; sürüm ölçütleri sessizce anlamsız | `seri` reddeder, `rapor` uyarır |
| Windows `git status` | `say` sonrası `M` (CRLF) | `.gitattributes` `veri/**` LF |
| Test | 104 | 148 (+44) |

## CLI akışı

```
ilk sonuç      git clone ... && cd mcp-census && uv run mcp-census rapor       ağ yok, 16 Eylül sayımı
örnekten üret  mcp-census --veri veri/ornek say   →  git diff boş               ağ yok, bayt bayt aynı
bugünün hâli   mcp-census indir --surum latest    (~5 dk, ağ)                   kayitlar-latest.jsonl
tam sayım      mcp-census indir  →  say  →  rapor  (~15 dk)                     veri/ altına
kıyas          mcp-census karsilastir ESKI YENI   çıkış 1 = kayıp kayıt var
seri           mcp-census seri                    yalnız tam, süzgeçsiz sayım
yanlış komut   hata: … + yardım: `mcp-census <komut> --help`                    çıkış 2
```

## Görsel dil (video sisteminden alınanlar)

Demo FRK-OS terminal sahnesinde; aynı sahne `mcp-vet` demosunda (`scripts/demo-uret.py`) kullanıldığı için sayfa şablonu oradan uyarlandı, yalnızca komutlar, renk kuralları ve başlık değişti.

| Ne | Nereden | Nerede |
|---|---|---|
| `zemin #0e0d0b`, panel `#14120e`, `yazi #f1ece2`, ilk vurgu `#ffc21a` | `sosyal/uret/tema.mjs` `klasik.akis` | zemin, panel, metin, sarı `$` isteği / sol çizgi / vurgulanan sayım satırları |
| `#ff4d6d` (mercan), `#ff7a1a` (turuncu) | `tema.mjs` klasik vurgular | `hata:` mercan, `DİKKAT` turuncu; yalnızca boyama, metin değişmez |
| `doku: "izgara"` | `tema.mjs` klasik | gövdede çok soluk sabit ızgara (`rgba(241,236,226,.045)`, 48 px) |
| JetBrains Mono (mono etiket) | `tema.mjs` `F.jb` | tüm terminal metni; SIL OFL 1.1, `assets/yazi/` (OFL metni yanında), tam kümeden |
| `terminal: "koyu"` sahnesi, 30 ms/harf yazma, satır satır çıktı | `tema.mjs` `tercih.terminal`, `sahne.js` terminal tekniği | `docs/demo/demo.html` |

Demoda sarıyla vurgulanan iki satır (`deposuz_sunucu`, `sadece_uzak_sunucu`) README'nin iki başlık bulgusudur; renk dışında metin değişmedi. Bilerek alınmayanlar: League Gothic başlık (README'de görsel başlık yok), geçişler (bir sayım çıktısının okunması gerekir), banner (`assets/banner.svg` profil üreticisinden; bu depoda elle değiştirilirse üreticinin sonraki çıktısı siler).

Kontrast (panel `#14120e` üstünde, WCAG göreli parlaklıktan hesaplandı): krem 15,9:1, sönük metin `#b6ae9d` 8,5:1, sarı 11,6:1, mercan 5,8:1, turuncu 7,2:1; hepsi ≥ 4,5:1. (Değerler bu görev sırasında yeniden hesaplandı.)

## Kararlar ve sınırlar

- **Başlık sayıları değişmedi.** 105.038 / 32.318 / 31.972 16 Eylül tam indirmesinin sayılarıdır ve o tarihle etiketli. 29 Eylül'ün 37.477'si farklı bir indirme yolundan (`latest`) geldiği ve ham dosyası depoda durmadığı için ayrı bir tabloda, "başlık sayısı değil" notuyla duruyor; seriye ya da `sayim.json`'a yazılmadı (o, aylık iş akışının işi: 1 Ekim 04:10 UTC).
- **Demo `mcp-census`'u PATH'ten çağırır** (`pip install .` ile kurulmuş dal sürümü); README'deki komut `uv run mcp-census`. Kurulum süresi ayrıca ölçüldü (`DENETIM.md`), demonun içinde koşturulmaz.
- Demo dikey 1080x1920 kaydı (`terminal.mp4`) depoya girmedi; günlük video hattı için `sosyal/medya/projeler/mcp-census/` altında.
- `argparse._` üzerinden çeviri bilerek dar tutuldu: anahtar bulunamazsa (Python sürümleri arasında iç mesajlar değişebilir) metin İngilizce kalır, davranış bozulmaz; test 3.11–3.14'te koşuyor.
- Sürüm, etiket, PyPI, dizin/awesome-list başvurusu, Pages ve GitHub description/homepage değişikliği **yapılmadı** (onay kapısı).
