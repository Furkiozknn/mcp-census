![mcp-census — resmî MCP Registry'nin yeniden üretilebilir sayımı: aynı uca sorulan aynı soru 105.038 satır, 32.318 ayrı sunucu ve 31.972 yayında cevabını veriyor](https://raw.githubusercontent.com/Furkiozknn/mcp-census/master/assets/banner.svg)

<div align="center">

[![CI](https://github.com/Furkiozknn/mcp-census/actions/workflows/ci.yml/badge.svg)](https://github.com/Furkiozknn/mcp-census/actions/workflows/ci.yml)

### **Resmî MCP Registry'nin yeniden üretilebilir sayımı.**

*Kaç sunucu var, kaçının okunacak kodu var, kaçı sizin makinenizde hiç çalışmıyor.*

![mcp-census raporu: 105.038 kayıt satırı, 32.318 ayrı sunucu adı, 31.972 aktif sunucu ve her satırın ne anlama geldiğinin tanımı](https://raw.githubusercontent.com/Furkiozknn/mcp-census/master/assets/demo.gif)

<sub>Gerçek çıktı, ağ olmadan: <code>veri/</code> klasöründeki indirilmiş anlık görüntüden üretiliyor, bu yüzden aynı komut yarın da aynı sayıları veriyor.</sub>

<br/>

![lisans](https://img.shields.io/badge/lisans-MIT-3fb950?style=flat-square&labelColor=0b0b0f)
![python](https://img.shields.io/badge/python-3.11%E2%80%933.14-3776ab?style=flat-square&labelColor=0b0b0f)
![bağımlılık](https://img.shields.io/badge/ba%C4%9F%C4%B1ml%C4%B1l%C4%B1k-0-3fb950?style=flat-square&labelColor=0b0b0f)
![test](https://img.shields.io/badge/test-104%20ge%C3%A7iyor-6cb6ff?style=flat-square&labelColor=0b0b0f)
![ölçülen](https://img.shields.io/badge/%C3%B6l%C3%A7%C3%BClen-32.318%20sunucu-c9a961?style=flat-square&labelColor=0b0b0f)

</div>

<details>
<summary><b>In English</b></summary>

<br>

**A reproducible count of the official MCP Registry.** It answers how many servers there are, how many have code you can read, and how many never run on your machine. The raw data, the code that produced each number and the definition of each number are all in this repository, so anyone can re-derive the numbers. The rest of this README is in Turkish.

On 16 September 2026 the whole registry was downloaded:

| Question | Answer |
|---|---:|
| Rows the `/v0/servers` endpoint returns | **105,038** |
| Distinct servers | **32,318** |
| Still `active` | **31,972** |

The endpoint returns one row per **version**, not per server. The mean is 3.25 versions per server, but the median is 1, so the inflation comes from a few repositories; one server alone accounts for 1,177 rows. Counting pages and calling the result "N servers" therefore overstates the total about threefold. The registry's `?version=latest` filter returns exactly one row per server (`mcp-census indir --surum latest`).

**A quarter of the registry has no code you can read.** 23.0% of servers declare no `repository` at all. 56.3% offer only a remote endpoint and no downloadable package, so whatever code you can read is not necessarily the code that runs.

```bash
git clone https://github.com/Furkiozknn/mcp-census && cd mcp-census
uv run mcp-census rapor                      # the 16 Sep 2026 count, from veri/sayim.json
uv run mcp-census --veri veri/ornek say      # a 500-record sample ships with the repo
uv run mcp-census --veri veri/ornek rapor
uv run mcp-census indir --surum latest       # the only command that uses the network (~5 min)
```

`say` (count), `rapor` (report), `karsilastir` (compare two snapshots) and `seri` (append a full count to the time series) read only files on disk. Zero runtime dependencies, Python 3.11–3.14. The test suite never touches the network. A scheduled workflow re-counts the registry monthly into [`veri/zaman-serisi.csv`](veri/zaman-serisi.csv).

</details>

---

## 30 saniyede dene

İndirme gerekmez: 16 Eylül 2026 sayımı ve 500 kayıtlık bir örnek depoda.
Gereken tek şey [uv](https://pypi.org/project/uv/) (Python 3.11+ yoksa uv onu da indirir).

```bash
git clone https://github.com/Furkiozknn/mcp-census && cd mcp-census
uv run mcp-census rapor                     # yukarıdaki GIF'teki rapor, ağ yok
uv run mcp-census --veri veri/ornek say     # örnekten sayımı baştan üret, ağ yok
uv run mcp-census --veri veri/ornek rapor
```

`say` deterministik: ikinci komut depodaki `veri/ornek/sayim.json` dosyasını
bayt bayt aynı yeniden yazar (`git status` temiz kalır; CI bunu her push'ta
denetliyor). Registry'nin bugünkü hâline bakmak için ağa çıkan tek komut:

```bash
uv run mcp-census --veri /tmp/deneme indir --azami-sayfa 2   # ~1 sn, 200 satır, "TAM DEĞİL" işaretli
uv run mcp-census --veri /tmp/deneme say
uv run mcp-census --veri /tmp/deneme rapor
```

## Neden

MCP ekosistemi hakkında dolaşan sayıların neredeyse tamamı tek bir satıcının
tek seferlik taramasından geliyor: *"kayıt defterinde N sunucu var"*,
*"popüler sunucuların %66'sında güvenlik bulgusu var"*. Bu sayılar
tartışılamıyor, çünkü ne veri ne de tarayıcı yayında. Yanlış olduklarını
göstermenin bir yolu yok — doğru olduklarını göstermenin de.

`mcp-census` bunun yerine üç şeyi birden veriyor: **ham veri**, **onu üreten
kod**, ve **her sayının tanımı**. Aynı komutu çalıştıran herkes aynı sonucu
alır; almıyorsa aradaki fark ölçülebilir (`mcp-census karsilastir`).

## İlk bulgu: "kaç sunucu var" sorusunun cevabı üçe katlanabiliyor

16 Eylül 2026'da resmî registry'nin tamamı indirildi.

| Soru | Cevap |
|---|---:|
| `/v0/servers` ucu kaç **satır** döndürüyor? | **105.038** |
| Kaç **ayrı sunucu** var? | **32.318** |
| Kaçı hâlâ **yayında** (`active`)? | **31.972** |

Fark, sunucu başına değil **sürüm** başına bir satır dönmesinden geliyor.
Sunucu başına ortalama 3,25 sürüm var — ama **medyan 1**. Yani şişmenin
kaynağı geniş bir eğilim değil, birkaç depo:

```
io.github.brilliantdirectories/brilliant-directories-mcp   1.177 sürüm
ai.bowmark/bowmark                                           828 sürüm
io.github.devantler-tech/ksail                               439 sürüm
```

Tek bir sunucu 1.177 satır üretiyor. Sayfaları sayıp "registry'de N sunucu
var" diyen bir ölçüm bu yüzden üç katı bir sayı bildirir.

**Doğru yol var ve kullanılmıyor:** registry `?version=latest` süzgecini
destekliyor ve tam olarak sunucu başına bir satır döndürüyor —
`mcp-census indir --surum latest`.

## İkinci bulgu: registry'nin dörtte birinin okunacak kodu yok

![Okunacak kodu olmayan kayıtlar, ölçekli: 32.318 sunucunun 7.439'unda repository alanı hiç yok, 18.183'ü yalnızca uzak uç sunuyor, 425'i ne paket ne uzak uç bildiriyor](https://raw.githubusercontent.com/Furkiozknn/mcp-census/master/assets/okunacak-kod.svg)

| Ölçüm | Sunucu | Oran |
|---|---:|---:|
| `repository` alanı **hiç yok** | 7.439 | **%23,0** |
| Yalnızca uzak uç sunuyor, indirilebilir paket yok | 18.183 | **%56,3** |
| Ne paket ne uzak uç bildiriyor — kurulacak bir şey yok | 425 | %1,3 |

İkisi de "kurmadan önce kodu oku" tavsiyesini doğrudan ilgilendiriyor:

- **%23'ünde okunacak kaynak yok.** Depo adresi bildirilmemiş. Statik bir
  denetleyici bu kayıtlar hakkında hiçbir şey söyleyemez.
- **%56'sı yalnızca uzak uç.** Okuyabildiğiniz kod, çalışan kod olmak
  zorunda değil; sunucu tarafında ne çalıştığını göremezsiniz.

Kaynak kodu olanların neredeyse tamamı GitHub'da (24.841), GitLab'de yalnızca
38 tane.

### Taşıma ve paketleme dağılımı

```
uzak uç          streamable-http 19.193 · sse 1.081
paket            npm 8.907 · pypi 3.785 · mcpb 1.221 · oci 919 · nuget 116 · cargo 51
durum            active 31.972 · deprecated 346
```

## Sayının kendisi hareket ediyor — ve bunu ölçüyoruz

Tam indirme ile `?version=latest` indirmesi arasında 15 dakika vardı. İkisi
farklı sayı verdi: **32.318** ve **32.321**.

```console
$ mcp-census karsilastir veri/kayitlar.jsonl veri/kayitlar-latest.jsonl
eski     32318 sunucu
yeni     32321 sunucu
eklenen      3   kaybolan 0

Fark yalnızca eklemeden ibaret; iki indirme arasında registry büyümüş. Sayım tutarlı.

eklenenler (ilk 50):
  + com.byjg/docs
  + com.docketnexus/docketnexus
  + io.github.API-Disk-Integrations/agent-mandate
```

**Kaybolan sıfır.** Fark tamamen ekleme — yani iki ölçüm arasında registry üç
sunucu büyümüş, indirmenin bir yeri eksik kalmamış. Bu ayrım önemli olduğu
için komut kayıp gördüğünde **çıkış 1** veriyor: CI'da eksik kalmış bir
indirme sessizce geçemez.

## Aynı soru, aylar sonra

Tek bir sayım bir fotoğraftır. `veri/sayim.json` 16 Eylül 2026'da ölçüldü ve o
günden sonra registry'nin nereye gittiğini söylemiyor — oysa bir sayım aracının
asıl değeri orada: "kaç sunucunun okunacak kodu yok" sorusunun cevabı artıyor
mu, azalıyor mu?

[`Sayim`](.github/workflows/sayim.yml) iş akışı ayın ilk günü registry'nin
tamamını indiriyor, sayıyor, önceki sayımla ölçüt ölçüt karşılaştırıyor
(tablo iş akışı özetinde) ve [`veri/zaman-serisi.csv`](veri/zaman-serisi.csv)
dosyasına bir satır ekliyor. Her tam koşu bir commit üretir — sayılar
oynamasa bile, çünkü "bu ay da ölçüldü ve aynıydı" bilgisi serinin kendisidir.

**Kısmi bir deneme seriye girmez.** İş akışı elle `azami_sayfa` ile
tetiklenirse yalnızca raporu özetine yazar, hiçbir şey commit etmez; ayrıca
`mcp-census seri` künyesinde `tam_mi: true` olmayan sayımı reddeder. 500
satırlık bir deneme seride "registry bir ayda %99 küçüldü" diye görünürdü.

Ham kayıtlar depoda durmuyor ve durmayacak: 105 bin satır, her ay yeniden.
Duran şey hesaplanmış sayım, onu üreten manifest ve serinin o ayki satırı —
üçü birlikte, ham veriye erişimi olmayan birinin de seriyi okuyabilmesi için
yeterli.

Ölçülmeyen bir ölçüt seride **boş** kalıyor, sıfıra çevrilmiyor: "o gün
ölçülmedi" ile "o gün sıfırdı" aynı şey değil, ve bir zaman serisinde bu fark
her şeydir. Sütun sırası sabit ve bir testle kilitli; bir CSV'nin sütun sırası
değişirse eski satırlar okunamaz hâle gelir.

## Kurulum

Depoyla birlikte (örnek veri ve sayım dahil) — önerilen yol:

```bash
git clone https://github.com/Furkiozknn/mcp-census && cd mcp-census
uv sync                      # çalışma zamanı bağımlılığı yok; yalnızca paketin kendisi
uv run mcp-census --help
```

Yalnızca komutu istiyorsanız (örnek veri gelmez, `indir` ile başlarsınız):

```bash
uv tool install git+https://github.com/Furkiozknn/mcp-census
mcp-census --version
```

PyPI'da henüz yayında değil; yayın iş akışı hazır ([`yayinla.yml`](.github/workflows/yayinla.yml)).

## Komutlar

Ağa çıkan tek komut `indir`. Diğerleri yalnızca diskteki dosyaları okur — bu
yüzden bir sayıya itiraz eden kişi aynı `kayitlar.jsonl` ile aynı sonucu
üretir. Bütün komutlar `--veri KLASÖR` ile çalışır (varsayılan: `veri`).

| Komut | Ne yapar | Okur → yazar |
|---|---|---|
| `indir` | Registry'yi sayfa sayfa çeker | ağ → `kayitlar.jsonl`, `manifest.json` |
| `say` | Sayımı üretir | `kayitlar.jsonl` (+ `manifest.json`) → `sayim.json` |
| `rapor` | Okunur metin (`--json`, `--yaz DOSYA`) | `sayim.json` → stdout |
| `karsilastir ESKI YENI` | İki indirmeyi sunucu adı düzeyinde karşılaştırır (`--json`) | iki `.jsonl` → stdout |
| `seri` | Tam bir sayımı zaman serisine ekler (`--onceki SAYIM`, `--ozet DOSYA`) | `sayim.json` → `zaman-serisi.csv` |

```bash
uv run mcp-census indir                        # tamamı: ~15 dk, ~1050 sayfa
uv run mcp-census indir --surum latest         # sunucu başına tek satır -> kayitlar-latest.jsonl (~5 dk)
uv run mcp-census indir --azami-sayfa 5        # hızlı deneme (künyede tam_mi: false)
uv run mcp-census rapor --json                 # makine okunur
uv run mcp-census karsilastir veri/kayitlar.jsonl veri/kayitlar-latest.jsonl
uv run mcp-census seri --onceki eski-sayim.json
```

`indir` seçenekleri: `--taban URL` (yalnızca `http(s)`), `--sayfa-boyu N`,
`--azami-sayfa N`, `--surum SUZGEC` (dosya adına girdiği için yalnızca harf,
rakam, `.`, `_`, `+`, `-`), `--sessiz`.

### Çıkış kodları ve hatalar

| Kod | Anlamı |
|---:|---|
| 0 | Başarılı |
| 1 | `karsilastir`: yeni indirmede **kaybolan** sunucu var (eksik indirme ya da registry silmiş) |
| 2 | Kullanım, ağ ya da dosya hatası — stderr'de tek satır `hata: …` |

| Gördüğünüz | Sebep ve çözüm |
|---|---|
| ``hata: veri/kayitlar.jsonl yok. Önce `mcp-census indir`.`` | Ham veri yok. Ya `indir`, ya `--veri veri/ornek`. |
| ``hata: veri/sayim.json yok. Önce `mcp-census say`.`` | `rapor` / `seri` sayımı okur; önce `say`. |
| `hata: …/kayitlar.jsonl:17 okunamadı: …` | O satır bozuk JSON; dosya yarım kalmış olabilir, yeniden `indir`. |
| `hata: … -> 3 denemede alınamadı: …` | Ağ ya da registry erişilemiyor (5xx ve kopmalar 3 kez denenir, 4xx denenmez). |
| `hata: kısmi indirme (manifest: tam_mi != true); seriye eklenmez` | `--azami-sayfa` ile indirilmiş veri; seri yalnızca tam sayım alır. |
| Raporun başında `DİKKAT bu veri kümesi kısmi` | Aynı sebep: sayılar tüm registry'yi temsil etmiyor. |

## Tasarım

**İndirme ile yorum ayrı.** `fetch.py` registry ne döndürdüyse onu yazar,
hiçbir şeyi yorumlamaz. Sayım ayrı bir adım. Böylece aynı ham veri üzerinde
başka biri başka bir analiz yazabilir, ya da aynı analizi yıllar sonra
yeniden koşturabilir.

**Her sayı tanımını taşır.** Bir `Bulgu` üç şey tutar: değer, tanım, payda.
Rapor tanımları da basar. Bir sayım aracında asıl kırılgan yer aritmetik
değil, "sunucu" kelimesinin ne demek olduğunun sessizce kaymasıdır — testler
tam olarak bunu koruyor.

**Künye, ölçümün kimliğidir.** Her indirme yanına bir `manifest.json` bırakır:
kaynak, zaman, sayfa sayısı ve satırların sha256 özeti. Aynı özeti üreten iki
indirme aynı veriyi görmüştür. "Hangi anlık görüntüye bakıyoruz" sorusunun
cevabı budur.

**Kısmi indirme tam sayım gibi görünmez.** `--azami-sayfa` kullanıldığında
künyeye `tam_mi: false` yazılır, rapor bunu başlıkta uyarı olarak basar,
komut stderr'e uyarı verir ve `seri` onu reddeder.

**Registry yanıtı güvenilmeyen veridir.** Yalnızca JSON olarak ayrıştırılır;
nesne olmayan satır diske yazılmadan reddedilir, bir sayfa (açılmış hâliyle)
32 MiB'ı aşarsa okunmaz. Ayrıntı: [SECURITY.md](SECURITY.md).

**Bağımlılık yok.** Bir ölçüm aracının kurulumunun kendisi bir tedarik
zinciri sorusu haline gelmemeli. Yalnızca standart kütüphane.

```
mcp_census/
  fetch.py     sayfalama, yeniden deneme, yanıt sınırı, künye, JSONL okuma/yazma
  analyze.py   sayım, dağılımlar, iki indirmenin karşılaştırması, zaman serisi
  cli.py       indir / say / rapor / karsilastir / seri
```

## Testler

```bash
uv run pytest        # 104 test, 1 saniyenin altında, hiçbiri ağa çıkmaz
```

`fetch` fonksiyonları test edilebilir bir `getirici` alıyor, CLI testleri
`_istek`'i yamalar. Testlerin koruduğu şeyler arasında: 4xx yeniden denenmez
ama 5xx denenir, tekrar eden imleç sonsuz döngüyü keser, sürüm satırları
dağılımları şişirmez, **hiçbir bulgu paydasından büyük olamaz** (koruma
yasası), kısmi sayım seriye girmez, `--surum` veri klasörünün dışına
yazdıramaz, gzip bombası belleği dolduramaz ve bozuk girdi yığın izi değil
`hata: …` verir.

CI her push'ta Python 3.11, 3.12, 3.13 ve 3.14'te testleri koşar, paketi
derleyip `twine check --strict` ile denetler ve tekerleği boş bir ortama
kurup çağırır.

## Bilinen sınırlar

- **Yalnızca resmî registry.** mcp.so, Smithery, Glama gibi başka kataloglar
  kapsam dışı. Oradaki sayılar bu sayımdan farklı çıkar ve çıkması normaldir.
- **Registry'nin kendi beyanına bakılır.** Bir kaydın `repository` alanı
  varsa "kaynak var" sayılıyor; o adresin gerçekten var olduğu, kaydın
  gerçekten o depodan geldiği doğrulanmıyor. Provenans ayrı bir iş — bunun
  için [`mcp-vet`](https://github.com/Furkiozknn/mcp-vet).
- **Kod okunmuyor.** Bu bir güvenlik tarayıcısı değil, bir sayım aracı.
  "%23'ünün kodu yok" cümlesi bir güvenlik iddiası değil, bir
  **denetlenebilirlik** ölçümü.
- **`isLatest` yoksa varsayım yapılır.** Sürüm işaretlenmemişse o adın en son
  görülen satırı alınır. Ölçülen veride bütün adlarda `isLatest` vardı
  (32.318 ad, 32.318 işaretli satır) ama kod bu varsayımı yine de taşıyor.
- **Tam indirme uzun sürer** (~15 dk, 1051 sayfa). Registry tarafında
  toplu dışa aktarma yok; sayfalama tek yol.

## Katkı ve güvenlik

[CONTRIBUTING.md](CONTRIBUTING.md) — geliştirme ortamı ve bu depoya özgü
kurallar (çalışma zamanı bağımlılığı yok, her sayı tanımını taşır, seri
sütunları değişmez). Bir sayıya itirazınız varsa "Bir sayıya itiraz" issue
şablonunu kullanın. Güvenlik açıkları: [SECURITY.md](SECURITY.md).
Sürüm geçmişi: [CHANGELOG.md](CHANGELOG.md).

## Bu ekosistemden başka projeler

- **[ajans-os](https://github.com/Furkiozknn/ajans-os)** — araştırma-önce kurulmuş, ADR ve sözleşmeli bir ajans OS'u
- **[mcp-vet](https://github.com/Furkiozknn/mcp-vet)** — bir MCP sunucusunun kaynağını kurmadan önce denetler

<sub>Hepsi tek bir aranabilir sayfada: **[furkiozknn.github.io](https://furkiozknn.github.io/)** — her kart, o deponun kendi <code>project-meta.json</code> dosyasından üretiliyor.</sub>

## Lisans

MIT — [LICENSE](LICENSE).
