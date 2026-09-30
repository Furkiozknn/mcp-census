#!/usr/bin/env python3
"""README terminal demosunu gercek komut ciktisindan uret.

    pip install .            # demo, kurulu `mcp-census`i calistirir (PATH)
    python scripts/demo-uret.py [cikti-klasoru]        # varsayilan: docs/demo

Ekrandaki hicbir sey elle yazilmadi. Asagidaki her komut, deponun temiz bir
yerel klonunda calistirilir; cikis kodu ve bastigi her sey kaydedilir, terminal
sayfasi o kaydi yazma animasyonuyla oynatir. `komutlar.txt` ayni kaydin duz
metni (komut, cikti, cikis kodu, sure, tarih).

Yazilan dosyalar:
    komutlar.txt      kayit
    demo.html         oynatma; ?dikey 1080x1920 yerlesim (baslik yok)
    demo.mp4/.gif     yatay kayit   } yalniz node + playwright + ffmpeg
    demo-dikey.mp4    dikey kayit   } varsa (scripts/demo-kayit.js)

`--sadece-kayit` videoyu atlar. `--kurulum` bos uv onbellegiyle soguk
`uvx --from git+... mcp-census --version` suresini olcup kurulum.txt'ye yazar
(ag ve GitHub ister).

Gorunum: gunluk videolarin FRK-OS terminal sahnesi (sosyal/uret/tema.mjs, tema
"klasik"): siyah #0e0d0b, krem #f1ece2, sari #ffc21a, JetBrains Mono (SIL OFL 1.1,
assets/yazi/).
"""
from __future__ import annotations

import base64
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# `set -o pipefail` acik: `| head` mcp-census'un kendi cikis kodunu bildirir.
# Komutlar deponun klonunda calisir; ornek veriyi say ile yeniden uretip
# git'in dosyayi degistirmedigi gosterilir; sonuncusu yanlis kullanimdir
# (araci ilk kez deneyen kisi buraya duser).
COMMANDS = [
    "mcp-census --version",
    "mcp-census rapor | head -n 17",
    "mcp-census --veri veri/ornek say",
    'git diff --exit-code veri/ornek/sayim.json; echo "git diff cikis kodu: $?"',
    "mcp-census --veri yok rapor",
]


def bash() -> str:
    found = shutil.which("bash")
    if not found:
        sys.exit("demo komutlari icin bash gerekli (Windows'ta Git Bash).")
    return found


def run_all(workdir: str) -> list[dict]:
    env = dict(os.environ, PYTHONIOENCODING="utf-8", NO_COLOR="1")
    record = []
    for command in COMMANDS:
        started = time.time()
        done = subprocess.run(
            [bash(), "-c", "set -o pipefail; " + command],
            cwd=workdir, env=env, capture_output=True, encoding="utf-8", errors="replace",
        )
        output = (done.stdout + done.stderr).replace("\r", "").rstrip()
        record.append({"k": command, "c": output, "kod": done.returncode,
                       "sure": round(time.time() - started, 2)})
    return record


def clone_head(workdir: str) -> str:
    """Deponun HEAD'inin temiz bir klonu; commit'i dondurur."""
    subprocess.run(["git", "clone", "-q", str(ROOT), workdir], check=True)
    done = subprocess.run(["git", "-C", workdir, "log", "-1", "--format=%h %cs"],
                          capture_output=True, encoding="utf-8")
    return done.stdout.strip()


def write_record(out: Path, record: list[dict], sha: str, version: str) -> None:
    now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    lines = [
        "# mcp-census terminal demosu: gercek komutlar, gercek cikti",
        f"# tarih: {now}",
        f"# surum: {version} (pip install . ile kuruldu, PATH'teki mcp-census)",
        f"# klon: deponun yerel klonu @ {sha}; veri/sayim.json 16 Eylul 2026 sayimi",
        "# her komut bash -c 'set -o pipefail; ...' ile klonda kosuldu; hicbir satir elle yazilmadi",
        "",
    ]
    for item in record:
        lines.append("$ " + item["k"])
        if item["c"]:
            lines.append(item["c"])
        lines.append(f"[cikis kodu {item['kod']}] ({item['sure']:.2f} s)")
        lines.append("")
    (out / "komutlar.txt").write_text("\n".join(lines), encoding="utf-8", newline="\n")


PAGE = r"""<!doctype html><html lang="tr"><meta charset="utf-8"><title>mcp-census demo</title>
<style>
@font-face{font-family:JB;font-weight:400;src:url(data:font/ttf;base64,__FONT400__) format("truetype")}
@font-face{font-family:JB;font-weight:700;src:url(data:font/ttf;base64,__FONT700__) format("truetype")}
:root{--zemin:#0e0d0b;--panel:#14120e;--krem:#f1ece2;--sari:#ffc21a;--sonuk:#b6ae9d;--mercan:#ff4d6d;--turuncu:#ff7a1a;--cam:#19d3e6}
html,body{margin:0;height:100%;background:var(--zemin)}
body{display:flex;align-items:center;justify-content:center;background-image:linear-gradient(rgba(241,236,226,.045) 1px,transparent 1px),linear-gradient(90deg,rgba(241,236,226,.045) 1px,transparent 1px);background-size:48px 48px}
.p{display:flex;flex-direction:column;width:1120px;height:640px;box-sizing:border-box;background:var(--panel);border:1px solid #3a352b;border-left:6px solid var(--sari);border-radius:8px;padding:22px 28px;font:400 20px/1.5 JB,Consolas,monospace;color:var(--krem);overflow:hidden;position:relative}
.b{font:700 13px JB,monospace;letter-spacing:.12em;color:var(--sari);margin:0 0 14px;text-transform:uppercase}
.y{color:var(--sari);font-weight:700}.d{color:var(--sonuk)}.k{color:var(--mercan)}.t{color:var(--turuncu)}.c{color:var(--cam)}
.w{flex:1;overflow:hidden;min-height:0}
pre{margin:0;white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}
.im{display:inline-block;width:11px;height:22px;background:var(--sari);vertical-align:-4px;margin-left:2px}
body.v .p{width:1040px;height:1760px;font-size:24px;padding:36px 36px}
body.v .b{display:none}
body.v .im{width:13px;height:28px;vertical-align:-6px}
@media (prefers-reduced-motion:reduce){.im{display:none}}
</style>
<div class="p"><div class="b">mcp-census &middot; ger&ccedil;ek komutlar, ger&ccedil;ek &ccedil;&#305;kt&#305;</div><div class="w"><pre id="t" aria-live="off"></pre></div></div>
<script>
const DIKEY=location.search.includes("dikey");
if(DIKEY)document.body.classList.add("v");
const K=__DATA__;
const HIZ=30; // harf basina ms
let olay=[],t=700;
for(const x of K){
  olay.push({t,tip:"komut",k:x.k}); t+=x.k.length*HIZ+300;
  const s=x.c?x.c.split("\n"):[];
  const adim=s.length>8?70:220;
  for(const l of s){olay.push({t,tip:"satir",l});t+=adim}
  t+=s.length?900:500;
}
const el=document.getElementById("t");
const esc=s=>s.replace(/&/g,"&amp;").replace(/</g,"&lt;");
// Renk yalniz sunum: hicbir karakteri degistirmez.
function boya(s){
  s=esc(s);
  s=s.replace(/^(hata:)/,'<span class="k">$1</span>');
  s=s.replace(/^(DİKKAT)/,'<span class="t">$1</span>');
  s=s.replace(/^(\s+(?:deposuz_sunucu|sadece_uzak_sunucu)\s.*)$/,'<span class="y">$1</span>');
  return s;
}
const t0=performance.now();
function ciz(){
  const now=performance.now()-t0;let g="";
  for(const o of olay){
    if(o.t>now)break;
    if(o.tip==="komut"){const n=Math.min(o.k.length,Math.floor((now-o.t)/HIZ));g+='<span class="y">$ </span>'+esc(o.k.slice(0,n))+(n<o.k.length?'<span class="im"></span>':"")+"\n"}
    else g+='<span class="d">'+boya(o.l)+"</span>\n";
  }
  if(now>olay[olay.length-1].t+300)g+='<span class="y">$ </span><span class="im"></span>';
  el.innerHTML=g;
  el.style.marginTop=Math.min(0,el.parentNode.clientHeight-el.getBoundingClientRect().height)+"px";
  requestAnimationFrame(ciz);
}
window.__bitis=olay[olay.length-1].t+1500;
ciz();
</script></html>
"""


def write_pages(out: Path, record: list[dict]) -> None:
    data = json.dumps([{"k": r["k"], "c": r["c"]} for r in record], ensure_ascii=False)
    fonts = ROOT / "assets" / "yazi"

    def embed(name: str) -> str:
        return base64.b64encode((fonts / name).read_bytes()).decode()

    html = (PAGE.replace("__DATA__", data)
            .replace("__FONT400__", embed("JetBrainsMono-Regular.ttf"))
            .replace("__FONT700__", embed("JetBrainsMono-Bold.ttf")))
    # Tek sayfa: varsayilan yatay, `?dikey` 1080x1920. Yazi tipleri gomulu (SIL OFL 1.1);
    # file:// ile tek basina oynar.
    (out / "demo.html").write_text(html, encoding="utf-8", newline="\n")


def record_video(out: Path) -> None:
    recorder = Path(__file__).with_name("demo-kayit.js")
    if not (shutil.which("node") and shutil.which("ffmpeg") and recorder.exists()):
        print("node/ffmpeg yok: yalniz komutlar.txt ve html yazildi.")
        return
    subprocess.run(["node", str(recorder), str(out)], check=True)


def measure_install(out: Path) -> None:
    """Bos uv onbellegiyle soguk `uvx` kurulumu, olculmus."""
    uvx = shutil.which("uvx")
    if not uvx:
        print("uvx yok: kurulum suresi atlandi.")
        return
    cache = tempfile.mkdtemp(prefix="mcp-census-uv-")
    env = dict(os.environ, UV_CACHE_DIR=cache, PYTHONIOENCODING="utf-8")
    command = [uvx, "--from", "git+https://github.com/Furkiozknn/mcp-census", "mcp-census", "--version"]
    rows = []
    for label in ("soguk (bos uv onbellegi)", "sicak (ayni onbellek)"):
        started = time.time()
        done = subprocess.run(command, env=env, capture_output=True, encoding="utf-8", errors="replace")
        rows.append(f"{label}: {time.time() - started:.2f} s, cikis {done.returncode}, "
                    f"cikti {done.stdout.strip()!r}")
    shutil.rmtree(cache, ignore_errors=True)
    stamp = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    (out / "kurulum.txt").write_text(
        "# uvx --from git+https://github.com/Furkiozknn/mcp-census mcp-census --version\n"
        f"# tarih: {stamp}\n" + "\n".join(rows) + "\n",
        encoding="utf-8", newline="\n",
    )
    print("\n".join(rows))


def main(argv: list[str]) -> int:
    flags = [a for a in argv if a.startswith("--")]
    args = [a for a in argv if not a.startswith("--")]
    out = Path(args[0]).resolve() if args else ROOT / "docs" / "demo"
    out.mkdir(parents=True, exist_ok=True)
    if not shutil.which("mcp-census"):
        sys.exit("mcp-census PATH'te yok: once depo kokunde `pip install .` calistirin.")
    version = subprocess.run(["mcp-census", "--version"], capture_output=True, encoding="utf-8").stdout.strip()
    with tempfile.TemporaryDirectory(prefix="mcp-census-demo-") as work:
        klon = os.path.join(work, "mcp-census")
        sha = clone_head(klon)
        record = run_all(klon)
    write_record(out, record, sha, version.replace("mcp-census ", ""))
    write_pages(out, record)
    if "--kurulum" in flags:
        measure_install(out)
    if "--sadece-kayit" not in flags:
        record_video(out)
    print(f"demo: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
