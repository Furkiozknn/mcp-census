# -*- coding: utf-8 -*-
"""`disa-aktar`: one row per server, with the same definitions as the count."""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import pytest

from mcp_census import analyze, cli, export, fetch

KOK = Path(__file__).resolve().parent.parent
ORNEK = KOK / "veri" / "ornek"


def kayit(ad, surum="1.0.0", *, enson=False, paketler=None, uclar=None, depo=None, aciklama="açıklama"):
    s = {"name": ad, "version": surum, "description": aciklama}
    if paketler is not None:
        s["packages"] = paketler
    if uclar is not None:
        s["remotes"] = uclar
    if depo is not None:
        s["repository"] = {"url": depo}
    return {"server": s, "_meta": {analyze.RESMI_META: {"status": "active", "isLatest": enson}}}


def test_one_row_per_server_with_its_latest_version_and_version_count():
    table = export.rows([
        kayit("io.github.a/x", "1.0.0"),
        kayit("io.github.a/x", "2.0.0", enson=True, paketler=[{"registryType": "npm"}]),
        kayit("com.b/y", uclar=[{"type": "sse"}], depo="https://GitLab.com/b/y"),
    ])
    assert [r["name"] for r in table] == ["com.b/y", "io.github.a/x"]
    x = table[1]
    assert x["version"] == "2.0.0" and x["version_count"] == 2 and x["is_latest_flag"] is True
    assert x["install_shape"] == "yalnizca_paket" and x["package_types"] == ["npm"]
    assert x["namespace"] == "io.github.a" and x["namespace_kind"] == "io.github"
    y = table[0]
    assert y["install_shape"] == "yalnizca_uzak" and y["remote_types"] == ["sse"]
    assert y["repository_host"] == "gitlab.com"


def test_export_agrees_with_the_count_on_the_sample():
    records = fetch.jsonl_oku(ORNEK / "kayitlar.jsonl")
    table = export.rows(records)
    count = analyze.sayim(records)
    b = {x["ad"]: x["deger"] for x in count["bulgular"]}
    assert len(table) == b["en_son_surumler"]
    assert sum(1 for r in table if not r["repository_url"]) == b["deposuz_sunucu"]
    assert sum(1 for r in table if r["install_shape"] == "yalnizca_uzak") == b["sadece_uzak_sunucu"]
    assert sum(1 for r in table if r["status"] == "active") == b["aktif_sunucu"]
    npm = sum(1 for r in table if "npm" in r["package_types"])
    assert npm == count["dagilimlar"]["paket_turu_sunucu"]["npm"]


def test_csv_has_the_fixed_header_and_joins_lists():
    text = export.to_csv(export.rows([kayit("a.b/c", paketler=[{"registryType": "pypi"},
                                                                {"registryType": "npm"}])]))
    lines = list(csv.reader(io.StringIO(text)))
    assert lines[0] == list(export.COLUMNS)
    row = dict(zip(lines[0], lines[1]))
    assert row["package_types"] == "npm;pypi"
    assert row["is_latest_flag"] == "false"


@pytest.mark.parametrize("hostile", ["=HYPERLINK(\"http://x\")", "+1+1", "-2", "@SUM(A1)", "\tx"])
def test_csv_cells_cannot_become_formulas(hostile):
    text = export.to_csv(export.rows([kayit("a.b/c", depo=hostile)]))
    row = dict(zip(*list(csv.reader(io.StringIO(text)))))
    assert row["repository_url"] == "'" + hostile


def test_jsonl_keeps_types_and_raw_values():
    line = export.to_jsonl(export.rows([kayit("a.b/c", depo="=x")])).splitlines()[0]
    obj = json.loads(line)
    assert list(obj) == list(export.COLUMNS)
    assert obj["repository_url"] == "=x" and obj["version_count"] == 1 and obj["package_types"] == []


def test_export_is_byte_stable_and_sorted():
    records = fetch.jsonl_oku(ORNEK / "kayitlar.jsonl")
    first = export.to_csv(export.rows(records))
    assert first == export.to_csv(export.rows(fetch.jsonl_oku(ORNEK / "kayitlar.jsonl")))
    names = [r["name"] for r in export.rows(records)]
    assert names == sorted(names)


class TestCommand:
    def test_writes_csv_next_to_the_data_by_default(self, tmp_path, capsys):
        veri = tmp_path / "veri"
        veri.mkdir()
        (veri / "kayitlar.jsonl").write_text(
            (ORNEK / "kayitlar.jsonl").read_text(encoding="utf-8"), encoding="utf-8")
        assert cli.main(["--veri", str(veri), "disa-aktar"]) == 0
        out = veri / "sunucular.csv"
        assert out.is_file() and b"\r\n" not in out.read_bytes()
        assert "sunucu ->" in capsys.readouterr().out

    def test_export_alias_and_stdout_jsonl(self, capsys):
        assert cli.main(["--veri", str(ORNEK), "export", "--bicim", "jsonl", "--cikti", "-"]) == 0
        lines = capsys.readouterr().out.splitlines()
        assert len(lines) == len(export.rows(fetch.jsonl_oku(ORNEK / "kayitlar.jsonl")))
        json.loads(lines[0])

    def test_explicit_input_file(self, tmp_path, capsys):
        src = tmp_path / "x.jsonl"
        fetch.jsonl_yaz([kayit("a.b/c")], src)
        out = tmp_path / "o.csv"
        assert cli.main(["disa-aktar", "--kayitlar", str(src), "--cikti", str(out)]) == 0
        assert out.read_text(encoding="utf-8").count("\n") == 2

    def test_missing_input_names_the_next_command(self, tmp_path, capsys):
        assert cli.main(["--veri", str(tmp_path), "disa-aktar"]) == 2
        err = capsys.readouterr().err
        assert "indir" in err and "veri/ornek" in err

    def test_unknown_format_is_a_usage_error(self, capsys):
        with pytest.raises(SystemExit) as exc:
            cli.main(["--veri", str(ORNEK), "disa-aktar", "--bicim", "xlsx"])
        assert exc.value.code == 2
