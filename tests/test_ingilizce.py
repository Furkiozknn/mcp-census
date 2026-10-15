# -*- coding: utf-8 -*-
"""English aliases: the same parser, the same functions, the same bytes."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from mcp_census import cli

KOK = Path(__file__).resolve().parent.parent
ORNEK = KOK / "veri" / "ornek"

ALIASES = {
    "download": "indir",
    "count": "say",
    "report": "rapor",
    "compare": "karsilastir",
    "series": "seri",
    "chart": "gorsel",
    "export": "disa-aktar",
}


@pytest.mark.parametrize("english,turkish", sorted(ALIASES.items()))
def test_alias_runs_the_same_function(english, turkish):
    extra = ["a.jsonl", "b.jsonl"] if turkish == "karsilastir" else []
    a = cli.kur().parse_args([english, *extra])
    b = cli.kur().parse_args([turkish, *extra])
    assert a.fn is b.fn


def test_help_lists_the_english_names(capsys):
    with pytest.raises(SystemExit):
        cli.main(["--help"])
    out = capsys.readouterr().out
    for english in ALIASES:
        assert f"({english})" in out
    assert "--data" in out


def _sample(tmp_path: Path) -> Path:
    veri = tmp_path / "veri"
    shutil.copytree(ORNEK, veri)
    return veri


def test_count_and_say_write_identical_files(tmp_path, capsys):
    tr = _sample(tmp_path / "tr")
    en = _sample(tmp_path / "en")
    assert cli.main(["--veri", str(tr), "say"]) == 0
    assert cli.main(["--data", str(en), "count"]) == 0
    assert (tr / "sayim.json").read_bytes() == (en / "sayim.json").read_bytes()


def test_report_json_matches_rapor(capsys):
    cli.main(["--veri", str(ORNEK), "rapor", "--json"])
    tr = capsys.readouterr().out
    cli.main(["report", "--data", str(ORNEK), "--json"])
    assert capsys.readouterr().out == tr


def test_english_flags_reach_the_same_destination():
    a = cli.kur().parse_args(["download", "--max-pages", "2", "--page-size", "50",
                              "--filter-version", "latest", "--quiet", "--base", "https://r.example"])
    assert (a.azami_sayfa, a.sayfa_boyu, a.surum, a.sessiz) == (2, 50, "latest", True)
    assert a.taban == "https://r.example"
    s = cli.kur().parse_args(["series", "--previous", "p.json", "--series-file", "s.csv", "--summary", "o.md"])
    assert (s.onceki, s.seri, s.ozet) == ("p.json", "s.csv", "o.md")
    c = cli.kur().parse_args(["chart", "--output", "x.svg", "--check"])
    assert (c.cikti, c.denetle) == ("x.svg", True)
    e = cli.kur().parse_args(["export", "--format", "jsonl", "--output", "-", "--records", "r.jsonl"])
    assert (e.bicim, e.cikti, e.kayitlar) == ("jsonl", "-", "r.jsonl")
    r = cli.kur().parse_args(["report", "--write", "out.txt"])
    assert r.yaz == "out.txt"


def test_data_after_the_command_works_too(capsys):
    a = cli.kur().parse_args(["report", "--data", "veri/ornek"])
    assert a.veri == "veri/ornek"


def test_usage_errors_name_one_spelling(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["download", "--max-pages", "0"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert err.startswith("hata: --azami-sayfa: en az 1"), err


def test_turkish_names_still_work_unchanged(capsys):
    a = cli.kur().parse_args(["--veri", "x", "indir", "--azami-sayfa", "3", "--sessiz"])
    assert (a.veri, a.azami_sayfa, a.sessiz) == ("x", 3, True)
