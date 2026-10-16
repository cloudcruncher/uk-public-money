"""Cabinet Office spend parser against the privacy-trimmed monthly CSV fixtures."""

from __future__ import annotations

import re
from decimal import Decimal
from functools import cache
from pathlib import Path

import pytest

from ukpm.parsers import FileMeta, LayoutError
from ukpm.parsers import cabinet_office_spend as co
from ukpm.provenance import problems
from ukpm.registry import FileEntry, Source

ROOT = Path(__file__).resolve().parent.parent
FX = ROOT / "tests/fixtures/cabinet_office"
SHA = "a" * 64
P = "cabinet_office_spend"
# month -> (data rows, total) from docs/sources/new-sources.md (scout, to the penny)
KNOWN = {
    "2025_09": (499, "112227426.43"),
    "2025_10": (524, "115830260.96"),
    "2026_03": (869, "261904761.53"),
    "2026_05": (562, "282202688.85"),
    "2026_08": (476, "110279506.39"),
}
ALL = sorted(p.stem[3:] for p in FX.glob("co_*.csv"))


def _meta(mm: str, path: Path | None = None, edition: str | None = None) -> FileMeta:
    ed = edition or mm.replace("_", "-")
    url = f"https://assets.publishing.service.gov.uk/media/x/{mm}.csv"
    f = FileEntry(
        f"co_{mm}",
        ed,
        "2026-09-24",
        url,
        "https://www.gov.uk/government/publications/cabinet-office-spend-data",
        "csv",
        SHA,
        "monthly_spend",
    )
    s = Source(
        "cabinet_office_spend",
        "Cabinet Office",
        "Cabinet Office spend over £25,000",
        "https://www.gov.uk/government/publications/cabinet-office-spend-data",
        "OGL-UK-3.0",
        "test",
        None,
        {},
        "USABLE",
        True,
        None,
        None,
        (f,),
    )
    return FileMeta(s, f, SHA, url, "2026-10-15T00:00:00Z", path or FX / f"co_{mm}.csv")


@cache
def _scan(mm: str):
    return co.scan(FX / f"co_{mm}.csv", _meta(mm))


def _one(rows, sid):
    (r,) = [r for r in rows if r.series_id == sid]
    return r


def test_twelve_fixtures_and_series_keys():
    assert len(ALL) == 12
    assert set(co.SERIES) == {
        f"{P}.{k}" for k in ("total", "transactions", "expense_type", "supplier")
    }


@pytest.mark.parametrize("mm", KNOWN)
def test_known_rows_and_totals_to_the_penny(mm):
    n, total = KNOWN[mm]
    rows = _scan(mm).rows
    t = _one(rows, f"{P}.total.{mm}")
    assert Decimal(repr(t.value)) == Decimal(total)
    assert _one(rows, f"{P}.transactions.{mm}").value == n
    assert t.unit == "gbp" and t.geography == "UK" and t.period_basis == "month"


def test_all_months_total_matches_scout_sum():
    total = sum(_one(_scan(m).rows, f"{P}.total.{m}").value for m in ALL)
    assert round(total, 2) == 1896163621.03


def test_expense_types_and_suppliers_add_up_to_total():
    for mm in ALL:
        rows = _scan(mm).rows
        t = _one(rows, f"{P}.total.{mm}").value
        for kind in ("expense_type", "supplier"):
            s = sum(r.value for r in rows if r.series_id.startswith(f"{P}.{kind}."))
            assert s == pytest.approx(t, abs=0.01)


def test_provenance_complete_and_ranges():
    rows = _scan("2025_09").rows
    assert rows and all(problems(r.prov) == [] for r in rows)
    t = _one(rows, f"{P}.total.2025_09")
    assert t.prov.sheet == "CSV" and t.prov.cell_or_range == "I2:I500"
    assert t.prov.file_sha256 == SHA and t.prov.status == "outturn"
    assert t.prov.vintage == "Cabinet Office spend over £25,000, September 2025"
    assert _one(rows, f"{P}.transactions.2025_09").prov.cell_or_range == "A2:A500"
    sub = [r for r in rows if r.series_id.startswith(f"{P}.expense_type.")]
    assert sub and all(
        r.prov.cell_or_range.startswith("I2:I500 where E=") and label_ok(r) for r in sub
    )
    # ids are unique per record content
    assert len({(r.series_id, r.prov.cell_or_range) for r in rows}) == len(rows)


def label_ok(r) -> bool:
    lab = co.label_of(r)
    return bool(lab) and f'E="{lab}"' in r.prov.cell_or_range


def test_label_of_and_quote_doubling():
    rows = _scan("2025_09").rows
    assert co.label_of(_one(rows, f"{P}.total.2025_09")) is None
    assert co.label_of(_one(rows, f"{P}.transactions.2025_09")) is None
    assert co._filter("G", 'A "B" Ltd') == ' where G="A ""B"" Ltd"'


def test_fiscal_year_mapping():
    assert _one(_scan("2026_03").rows, f"{P}.total.2026_03").fiscal_year == "2025-26"
    assert _one(_scan("2026_04").rows, f"{P}.total.2026_04").fiscal_year == "2026-27"
    assert _one(_scan("2025_09").rows, f"{P}.total.2025_09").fiscal_year == "2025-26"


def test_blank_and_placeholder_rows_are_reported_not_silent():
    aug = _scan("2026_08")
    assert [s.reason for s in aug.skipped] == ["blank"] * 130
    assert aug.transactions == 476
    may = _scan("2026_05")
    assert [(s.row, s.reason) for s in may.skipped] == [(149, "placeholder")]
    assert may.transactions == 562
    assert _scan("2025_09").skipped == []


def test_no_personal_or_row_level_fields():
    for mm in ALL:
        for r in _scan(mm).rows:
            assert r.series_id.split(".")[1] in (
                "total",
                "transactions",
                "expense_type",
                "supplier",
            )
    text = (FX / "co_2026_03.csv").read_text("cp1252").splitlines()[1:]
    assert all(line.split(",")[0] == "" for line in text if line.strip(", "))  # Ref blanked


def test_fixture_privacy_trim():
    big = {}
    for mm in ALL:
        for r in _scan(mm).rows:
            if r.series_id.startswith(f"{P}.supplier."):
                name = re.sub(r"^.*\.\d{4}_\d{2}\.", "", r.series_id)
                big[name] = big.get(name, 0) + r.value
    assert "withheld_fixture" in big
    # every supplier left in the fixtures is a >= 1m supplier (or the placeholder name)
    assert all(v >= 1_000_000 for k, v in big.items() if k not in ("withheld_fixture", "unnamed"))


def _csv(tmp_path, body: bytes, name="x.csv"):
    p = tmp_path / name
    p.write_bytes(body)
    return p


HEAD = ",".join(co.HEADERS) + "\r\n"


def test_cp1252_and_utf8_sig_decode(tmp_path):
    line = '1,CAB,Cabinet Office,01-Sep-25,Prof,Area,AtkinsRéalis,10,"1,000.50"\r\n'
    a = _csv(tmp_path, (HEAD + line).encode("cp1252"), "a.csv")
    b = _csv(tmp_path, (HEAD + line).encode("utf-8-sig"), "b.csv")
    for p in (a, b):
        rows = co.parse(p, _meta("2025_09", p))
        assert _one(rows, f"{P}.supplier.2025_09.atkinsr_alis").value == 1000.5
        assert co.label_of(_one(rows, f"{P}.supplier.2025_09.atkinsr_alis")) == "AtkinsRéalis"


def test_bad_amount_raises_with_row_number(tmp_path):
    body = HEAD + "1,CAB,CO,01-Sep-25,Prof,A,S,1,10.00\r\n2,CAB,CO,01-Sep-25,Prof,A,S,2,n/a\r\n"
    p = _csv(tmp_path, body.encode())
    with pytest.raises(LayoutError, match="row 3"):
        co.parse(p, _meta("2025_09", p))


def test_negative_amounts_and_slug_collisions(tmp_path):
    body = (
        HEAD
        + '1,CAB,CO,01-Sep-25,Prof,A,Acme Ltd,1,"100.00"\r\n'
        + '2,CAB,CO,01-Sep-25,Prof,A,ACME LTD.,2,"(40.00)"\r\n'
        + '3,CAB,CO,01-Sep-25,Prof,A,"Say ""hi"" Co",3,"-5.00"\r\n'
    )
    p = _csv(tmp_path, body.encode())
    rows = co.parse(p, _meta("2025_09", p))
    assert _one(rows, f"{P}.total.2025_09").value == 55.0
    assert _one(rows, f"{P}.supplier.2025_09.acme_ltd").value == 100.0
    assert _one(rows, f"{P}.supplier.2025_09.acme_ltd_2").value == -40.0
    r = _one(rows, f"{P}.supplier.2025_09.say_hi_co")
    assert r.prov.cell_or_range == 'I2:I4 where G="Say ""hi"" Co"'
    assert co.label_of(r) == 'Say "hi" Co'


def test_header_variants_and_column_order(tmp_path):
    body = (
        "Departmental Family,ref,Entity,Date,Expense Type,Expense Area,Supplier,"
        "Transaction number,AMOUNT\r\n"
        "CAB,1,CO,01-Sep-25,Prof,A,S,1,7.00\r\n"
    )
    p = _csv(tmp_path, body.encode())
    rows = co.parse(p, _meta("2025_09", p))
    t = _one(rows, f"{P}.total.2025_09")
    assert t.value == 7.0 and t.prov.cell_or_range == "I2:I2"
    assert _one(rows, f"{P}.transactions.2025_09").prov.cell_or_range == "B2:B2"


def test_missing_header_and_bad_encoding_and_edition(tmp_path):
    p = _csv(tmp_path, b"Ref,Entity,Amount\r\n1,CO,5\r\n")
    with pytest.raises(LayoutError):
        co.parse(p, _meta("2025_09", p))
    p = _csv(tmp_path, HEAD.encode() + b"1,CAB,CO,d,Prof,A,S\x81,1,5\r\n")
    with pytest.raises(LayoutError):
        co.parse(p, _meta("2025_09", p))
    p = _csv(tmp_path, (HEAD + "1,CAB,CO,d,Prof,A,S,1,5\r\n").encode())
    with pytest.raises(LayoutError):
        co.parse(p, _meta("2025_09", p, edition="September 2025"))
