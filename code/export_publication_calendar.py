"""Export Appendix H1 from the preserved publication calendar and source pages.

The export documents publication dates, not the historical availability of each
statistical cell. No network access or inference about original data vintages is
performed. Run with ``--check`` to verify the committed CSV and source index.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import tempfile
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

SOURCE_DIRECTORY = Path("raw/supplementary_sources_261028_v2/source_release")
CALENDAR_FILENAME = "release_calendar_H1_2013_2025.json"
EXPECTED_YEARS = tuple(range(2013, 2026))
CSV_HEADER = ("연도", "게시일", "공식 게시물 제목", "원문")


class PublicationTitleParser(HTMLParser):
    """Read the publication title without including page navigation text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.titles: list[str] = []
        self._parts: list[str] = []
        self._collecting = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        classes = (dict(attrs).get("class") or "").split()
        if tag == "h4" and "bv_title" in classes:
            self._collecting = True
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._collecting:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "h4" and self._collecting:
            self.titles.append(" ".join("".join(self._parts).split()))
            self._collecting = False


def source_title(payload: bytes, source: Path) -> str:
    parser = PublicationTitleParser()
    parser.feed(payload.decode("utf-8-sig"))
    if len(parser.titles) != 1 or not parser.titles[0]:
        raise ValueError(f"Expected one publication title in {source}")
    return parser.titles[0]


def validate_urls(publication_url: str, pdf_url: str, year: int) -> None:
    publication, pdf = urlsplit(publication_url), urlsplit(pdf_url)
    for value in (publication, pdf):
        if value.scheme != "https" or value.netloc != "mods.go.kr":
            raise ValueError(f"Unexpected source host for {year}")
    if publication.path != "/board.es" or pdf.path != "/boardDownload.es":
        raise ValueError(f"Unexpected source endpoint for {year}")
    page_query, pdf_query = parse_qs(publication.query), parse_qs(pdf.query)
    for key in ("bid", "list_no"):
        if not page_query.get(key) or page_query[key] != pdf_query.get(key):
            raise ValueError(
                f"Publication and PDF identifiers differ for {year}: {key}"
            )
    if page_query.get("act") != ["view"] or not pdf_query.get("seq"):
        raise ValueError(f"Incomplete publication or PDF address for {year}")


def build_exports(root: Path) -> dict[str, bytes]:
    source_dir = root / SOURCE_DIRECTORY
    calendar_path = source_dir / CALENDAR_FILENAME
    calendar_bytes = calendar_path.read_bytes()
    calendar = json.loads(calendar_bytes)
    if not isinstance(calendar, list):
        raise ValueError("The publication calendar must contain a list")
    years = [record.get("year") for record in calendar]
    if years != list(EXPECTED_YEARS):
        raise ValueError("The calendar must contain each year 2013–2025 once, in order")

    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(CSV_HEADER)
    sources: list[dict[str, object]] = []
    for record in calendar:
        year = record["year"]
        release_date = date.fromisoformat(record["release_date"])
        if release_date.year != year or release_date.month != 10:
            raise ValueError(f"Unexpected publication date for {year}: {release_date}")
        validate_urls(record["source_url"], record["pdf_url"], year)
        html_path = source_dir / f"{year}_H1_page.html"
        html_bytes = html_path.read_bytes()
        title = source_title(html_bytes, html_path)
        # Appendix H1 uses compact link labels; retain the complete source title below.
        display_title = re.sub(r"\s+", "", title)
        writer.writerow((year, release_date.isoformat(), display_title, "PDF"))
        sources.append(
            {
                "year": year,
                "publication_date": release_date.isoformat(),
                "title": title,
                "display_title": display_title,
                "publication_url": record["source_url"],
                "pdf_url": record["pdf_url"],
                "preserved_page": html_path.relative_to(root).as_posix(),
                "preserved_page_sha256": hashlib.sha256(html_bytes).hexdigest(),
                "pdf_sha256_recorded_in_calendar": record["pdf_sha256"],
            }
        )

    index = {
        "table": "H1",
        "source_calendar": calendar_path.relative_to(root).as_posix(),
        "source_calendar_sha256": hashlib.sha256(calendar_bytes).hexdigest(),
        "scope": "Official publication dates and source links from preserved records; "
        "individual statistical cells' original publication and revision vintages "
        "are not established by this export.",
        "records": sources,
    }
    return {
        "table_H1.csv": buffer.getvalue().encode("utf-8-sig"),
        "table_H1_sources.json": (
            json.dumps(index, ensure_ascii=False, indent=2) + "\n"
        ).encode("utf-8"),
    }


def write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument(
        "--output-dir", type=Path, help="Default: ROOT/results/paper_tables"
    )
    parser.add_argument(
        "--check", action="store_true", help="Verify existing exports without writing"
    )
    args = parser.parse_args()
    root = args.root.resolve()
    output_dir = args.output_dir or root / "results/paper_tables"
    try:
        exports = build_exports(root)
        if args.check:
            mismatches = [
                name
                for name, payload in exports.items()
                if not (output_dir / name).is_file()
                or (output_dir / name).read_bytes() != payload
            ]
            if mismatches:
                raise ValueError("Missing or stale exports: " + ", ".join(mismatches))
        else:
            for name, payload in exports.items():
                write_atomic(output_dir / name, payload)
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Publication calendar export failed: {error}\n")
    print(
        json.dumps(
            {
                "status": "verified" if args.check else "exported",
                "years": 13,
                "files": sorted(exports),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
