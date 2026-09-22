"""Generates SIGNAL_REGISTER_STATUS.md: where each of the register's 200
positions stands against what the platform actually implements.

Run from the repository root:

    python shared/docs/generate_signal_register_status.py

WHY A SCRIPT. The register grows and the catalogue grows, at different
times and by different hands. A status page written once by hand is
wrong within a week and nobody can tell which half is stale; this one is
re-run and the diff is the answer. It never touches the workbook - it
only reads it.

NO openpyxl. It is not a dependency of this repository and adding one
for a document generator would be the wrong trade, so the sheet is read
with zipfile + ElementTree: an .xlsx is a zip of XML, and the part this
needs (shared strings and one worksheet's cells) is small.

WHAT IT DECIDES. A register row is matched against the catalogue by id,
with <placeholders> normalised so SEC.ZONE.<zone_id>.ARMED matches the
catalogue's own pattern. Everything else is classified by its GROUP,
which is the honest unit: "PWR needs a point given a role in Studio" is
a statement about the whole group, not about thirteen separate rows.
"""
import json
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import OrderedDict

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

WORKBOOK = os.path.join(_HERE, "EPW_Rejestr_Bitow_Wewnetrznych_V2.xlsx")
SHEET = "01_REJESTR_BITOW"
OUTPUT = os.path.join(_HERE, "SIGNAL_REGISTER_STATUS.md")

_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_RNS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_PLACEHOLDER = re.compile(r"<[^>]*>")


# ---------------------------------------------------------------- the sheet

def _shared_strings(archive):
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    return ["".join(t.text or "" for t in si.iter(_NS + "t"))
            for si in root.findall(_NS + "si")]


def _sheet_path(archive, name):
    rels = {rel.get("Id"): rel.get("Target")
            for rel in ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))}
    for sheet in ET.fromstring(archive.read("xl/workbook.xml")).iter(_NS + "sheet"):
        if sheet.get("name") == name:
            target = (rels.get(sheet.get(_RNS + "id")) or "").lstrip("/")
            return target if target.startswith("xl/") else "xl/" + target
    raise SystemExit("no sheet %r in %s" % (name, WORKBOOK))


def _column_index(reference):
    letters = re.match(r"([A-Z]+)", reference or "A").group(1)
    index = 0
    for char in letters:
        index = index * 26 + (ord(char) - 64)
    return index - 1


def read_register():
    """[{column heading: value}] for every non-empty row of the sheet."""
    archive = zipfile.ZipFile(WORKBOOK)
    strings = _shared_strings(archive)
    root = ET.fromstring(archive.read(_sheet_path(archive, SHEET)))

    rows = []
    for row in root.iter(_NS + "row"):
        cells = {}
        for cell in row.findall(_NS + "c"):
            kind = cell.get("t")
            if kind == "s":
                value = cell.find(_NS + "v")
                text = strings[int(value.text)] if value is not None and value.text else ""
            elif kind == "inlineStr":
                inline = cell.find(_NS + "is")
                text = "".join(t.text or "" for t in inline.iter(_NS + "t")) if inline is not None else ""
            else:
                value = cell.find(_NS + "v")
                text = value.text if value is not None and value.text else ""
            cells[_column_index(cell.get("r", ""))] = (text or "").strip()
        rows.append(cells)

    if not rows:
        raise SystemExit("the register sheet is empty")
    headings = [rows[0].get(i, "") for i in range(max(rows[0]) + 1)]
    entries = []
    for cells in rows[1:]:
        record = {headings[i]: cells.get(i, "") for i in range(len(headings))}
        if record.get("ID / Wzorzec"):
            entries.append(record)
    return entries


# --------------------------------------------------------------- the verdict

def _normalise(signal_id: str) -> str:
    """"SEC.ZONE.<zone_id>.ARMED" and "SEC.ZONE.<id>.ARMED" are the same
    signal written by two hands."""
    return _PLACEHOLDER.sub("<>", signal_id or "").upper()


# What is waiting on what. Keyed by the register's own GROUP column,
# because that is the unit these decisions are actually made in.
_PENDING = OrderedDict([
    # POWER and UPS: served since etap 3 (EPM's register block) and etap 4
    # (a DI point with a role) - a row of theirs missing from the catalogue
    # is plainly "do zrobienia" now, not waiting on anything.
    ("DEVICE HEALTH", ("czeka na firmware",
                       "wymaga rejestrów diagnostycznych w firmware karty - mapa rejestrów ELA01")),
    ("DIAGNOSTICS", ("czeka na firmware",
                     "wymaga rejestrów diagnostycznych w firmware karty - mapa rejestrów ELA01")),
    ("INTER-CONTROLLER", ("przyszłość", "sygnały między sterownikami, bez implementacji")),
    ("USER INTERNAL", ("poza katalogiem",
                       "to markery użytkownika (M.*) z działu Sygnały, nie katalog platformy")),
    ("PHYSICAL I/O", ("poza katalogiem",
                      "adres fizyczny, opisany gramatyką adresów (shared/addressing.py)")),
])


def classify(entry, catalog_by_id, renames):
    """(status, note) for one register row."""
    signal_id = entry["ID / Wzorzec"]
    catalog = catalog_by_id.get(_normalise(signal_id))
    if catalog is not None:
        if catalog.get("runtime") == "served":
            return "w katalogu i obsłużony", ""
        return "w katalogu, bez źródła", "nazwa ustalona, nic jeszcze nie wylicza wartości"

    group = (entry.get("Grupa") or "").upper()
    for key, (status, note) in _PENDING.items():
        if group.startswith(key):
            return status, note

    renamed = renames.get(_normalise(signal_id))
    if renamed:
        return "nazwa zmieniona", "teraz %s" % renamed
    return "do zrobienia", "w zakresie katalogu, jeszcze nie dodany"


# ---------------------------------------------------------------- the report

def build() -> str:
    from shared.logic import system_signals
    from shared.logic.signal_renames import RENAMES, by_provenance

    entries = read_register()
    # The catalog AS WRITTEN - patterns included. get_all_signals() with
    # no project expands a pattern to nothing, which would report every
    # per-zone signal as missing on the very commit that added it.
    catalog = system_signals.raw_signals()
    catalog_by_id = {_normalise(s["id"]): s for s in catalog}
    renames = {_normalise(old): new for old, (new, _p) in RENAMES.items()}

    verdicts = [(entry, classify(entry, catalog_by_id, renames)) for entry in entries]

    counts = OrderedDict()
    for _entry, (status, _note) in verdicts:
        counts[status] = counts.get(status, 0) + 1

    out = []
    w = out.append
    w("# Rejestr sygnałów — stan wdrożenia")
    w("")
    w("**Plik generowany.** Nie edytuj go ręcznie — uruchom")
    w("`python shared/docs/generate_signal_register_status.py` z korzenia repo.")
    w("Źródłem jest `EPW_Rejestr_Bitow_Wewnetrznych_V2.xlsx` (arkusz")
    w("`%s`), porównywany z `shared/logic/system_signals_catalog.json`" % SHEET)
    w("(wersja katalogu **%s**). Arkusz jest tylko czytany." % system_signals.get_catalog_version())
    w("")
    w("Pozycji w rejestrze: **%d**." % len(entries))
    w("")
    w("| stan | pozycji |")
    w("|---|---:|")
    for status, count in sorted(counts.items(), key=lambda kv: -kv[1]):
        w("| %s | %d |" % (status, count))
    w("")

    w("## Co znaczy każdy stan")
    w("")
    w("- **w katalogu i obsłużony** — sygnał jest w katalogu platformy, a sterownik")
    w("  realnie wylicza jego wartość. Logika może go użyć.")
    w("- **w katalogu, bez źródła** — nazwa ustalona, ale nic jeszcze nie liczy")
    w("  wartości. Panel Sygnały pokazuje to wprost jako „brak źródła”.")
    w("- **czeka na firmware** — potrzebne rejestry diagnostyczne w firmware karty.")
    w("- **przyszłość** — koncepcja bez implementacji po żadnej stronie.")
    w("- **poza katalogiem** — sygnał należy do innej warstwy (markery użytkownika,")
    w("  adresy fizyczne), więc katalog platformy nie jest jego miejscem.")
    w("- **do zrobienia** — mieści się w katalogu, jeszcze go tam nie ma.")
    w("")

    w("## Zmiany nazw")
    w("")
    w("Decyzja właściciela (2026-09-21): prefiks alarmówki to `SEC.`, a komendy")
    w("stają się żądaniami `REQ.SEC.*`. To **nie** jest zamiana prefiksu —")
    w("szczegóły i powód w `shared/logic/signal_renames.py`.")
    w("")
    w("### Nazwy wzięte z rejestru (%d)" % len(by_provenance("register")))
    w("")
    w("| było | jest |")
    w("|---|---|")
    for old, new in by_provenance("register"):
        w("| `%s` | `%s` |" % (old, new))
    w("")
    w("### Nazwy ustalone tutaj, przyjęte (%d)" % len(by_provenance("accepted")))
    w("")
    w("Te sygnały **nie mają wiersza w rejestrze** — sterownik obsługuje je dziś,")
    w("a rejestr ich nie obejmuje (brak dozoru częściowego, sygnalizatora i linii")
    w("napadowej; rejestr jest też wyłącznie BOOL-owy). Nazwano je konsekwentnie")
    w("z gramatyką rejestru i **właściciel przyjął je 2026-09-21** — to nie jest")
    w("pozycja oczekująca. Wypisane osobno tylko po to, żeby przyszła wersja")
    w("rejestru wiedziała, które nazwy powstały tutaj.")
    w("")
    w("| było | jest |")
    w("|---|---|")
    for old, new in by_provenance("accepted"):
        w("| `%s` | `%s` |" % (old, new))
    w("")

    w("## Pozycje rejestru")
    w("")
    w("| ID / wzorzec | grupa | kierunek | stan | uwaga |")
    w("|---|---|---|---|---|")
    for entry, (status, note) in verdicts:
        w("| `%s` | %s | %s | %s | %s |" % (
            entry["ID / Wzorzec"], entry.get("Grupa", ""),
            entry.get("Kierunek", ""), status, note))
    w("")

    extra = sorted(s["id"] for s in catalog
                   if _normalise(s["id"]) not in {_normalise(e["ID / Wzorzec"]) for e in entries})
    w("## W katalogu, poza rejestrem (%d)" % len(extra))
    w("")
    w("Sygnały, które platforma udostępnia, a których rejestr nie opisuje —")
    w("kandydaci do dopisania do arkusza.")
    w("")
    for signal_id in extra:
        w("- `%s`" % signal_id)
    w("")
    return "\n".join(out) + "\n"


def main():
    text = build()
    with open(OUTPUT, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    print("zapisano %s (%d znaków)" % (os.path.relpath(OUTPUT, _REPO), len(text)))


if __name__ == "__main__":
    main()
