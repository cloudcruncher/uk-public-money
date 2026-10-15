"""One spreadsheet reader for xlsx and ods (python-calamine).

Row 0 is spreadsheet row 1 and column 0 is column A, so indices map to real A1 addresses.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from python_calamine import CalamineWorkbook


def a1(row_idx: int, col_idx: int) -> str:
    """0-based (row, col) to an A1 address, e.g. (45, 1) -> 'B46'."""
    if row_idx < 0 or col_idx < 0:
        raise ValueError("negative index")
    n, letters = col_idx + 1, ""
    while n:
        n, r = divmod(n - 1, 26)
        letters = chr(65 + r) + letters
    return f"{letters}{row_idx + 1}"


class Book:
    def __init__(self, wb: CalamineWorkbook):
        self._wb = wb
        self._cache: dict[str, list[list[Any]]] = {}

    @property
    def sheet_names(self) -> list[str]:
        return list(self._wb.sheet_names)

    def rows(self, sheet: str) -> list[list[Any]]:
        if sheet not in self._cache:
            if sheet not in self.sheet_names:
                raise KeyError(f"sheet {sheet!r} not found; have {self.sheet_names}")
            self._cache[sheet] = self._wb.get_sheet_by_name(sheet).to_python(skip_empty_area=False)
        return self._cache[sheet]

    def find(self, sheet: str, text: str) -> tuple[int, int]:
        """First cell whose stripped, case-folded text equals `text` (row-major)."""
        want = text.strip().casefold()
        for r, row in enumerate(self.rows(sheet)):
            for c, v in enumerate(row):
                if isinstance(v, str) and v.strip().casefold() == want:
                    return r, c
        raise LookupError(f"{text!r} not found in sheet {sheet!r}")


def open_book(path: str | Path) -> Book:
    return Book(CalamineWorkbook.from_path(str(path)))


def find(book: Book, sheet: str, text: str) -> tuple[int, int]:
    return book.find(sheet, text)
