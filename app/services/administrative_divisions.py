from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

from app.models import AdministrativeDivision
from app.repositories import AdministrativeDivisionRepository


REFERENCE_WORKBOOK_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "references"
    / "raw"
    / "china_administrative.xlsx"
)

_XML_NS = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_REL_ID_ATTR = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


@dataclass(slots=True, frozen=True)
class AdministrativeDivisionSeedRow:
    name: str
    division_type: str
    level: int
    code: str
    adcode: str
    parent_code: str | None
    sort_order: int


@dataclass(slots=True, frozen=True)
class AdministrativeDivisionNode:
    code: str
    adcode: str
    name: str
    division_type: str
    level: int
    parent_code: str | None
    has_children: bool
    is_virtual: bool = False


class AdministrativeDivisionQueryService:
    def __init__(self, administrative_division_repository: AdministrativeDivisionRepository) -> None:
        self.administrative_division_repository = administrative_division_repository

    def list_children(
        self,
        parent_code: str | None = None,
        *,
        parent_level: int | None = None,
    ) -> list[AdministrativeDivisionNode]:
        normalized_parent_code = _normalize_code(parent_code)
        if normalized_parent_code is None:
            if parent_level is not None:
                raise ValueError("parent_level requires parent_code.")
            return [self._to_node(item) for item in self.administrative_division_repository.list_roots()]

        if parent_level is None:
            raise ValueError("parent_level is required when parent_code is provided.")
        if parent_level < 1 or parent_level > 4:
            raise ValueError("parent_level must be between 1 and 4.")

        if not self._parent_exists(normalized_parent_code, parent_level):
            raise LookupError(f"Administrative division parent {normalized_parent_code} (level {parent_level}) does not exist.")

        raw_children = self.administrative_division_repository.list_by_parent_code(normalized_parent_code)
        if parent_level == 1:
            level_2_children = [item for item in raw_children if item.level == 2]
            if level_2_children:
                return [self._to_node(item) for item in level_2_children]
            level_3_children = [item for item in raw_children if item.level == 3]
            if level_3_children:
                return [self._build_virtual_city_node(normalized_parent_code)]
            return []

        expected_child_level = parent_level + 1
        return [self._to_node(item) for item in raw_children if item.level == expected_child_level]

    def _parent_exists(self, code: str, level: int) -> bool:
        if self.administrative_division_repository.get_by_code_and_level(code, level) is not None:
            return True
        if level == 2 and self.administrative_division_repository.get_by_code_and_level(code, 1) is not None:
            return any(item.level == 3 for item in self.administrative_division_repository.list_by_parent_code(code))
        return False

    def _build_virtual_city_node(self, province_code: str) -> AdministrativeDivisionNode:
        province = self.administrative_division_repository.get_by_code_and_level(province_code, 1)
        if province is None:
            raise LookupError(f"Administrative division parent {province_code} (level 1) does not exist.")
        return AdministrativeDivisionNode(
            code=province.code,
            adcode=province.adcode,
            name=province.name,
            division_type=province.division_type,
            level=2,
            parent_code=province.code,
            has_children=True,
            is_virtual=True,
        )

    def _to_node(self, item: AdministrativeDivision) -> AdministrativeDivisionNode:
        return AdministrativeDivisionNode(
            code=item.code,
            adcode=item.adcode,
            name=item.name,
            division_type=item.division_type,
            level=item.level,
            parent_code=item.parent_code,
            has_children=self.administrative_division_repository.has_children(item.code),
            is_virtual=False,
        )


def load_administrative_division_seed_rows(path: Path = REFERENCE_WORKBOOK_PATH) -> list[AdministrativeDivisionSeedRow]:
    if not path.exists():
        raise FileNotFoundError(f"Administrative division reference workbook not found: {path}.")

    rows: list[AdministrativeDivisionSeedRow] = []
    for sort_order, raw_row in enumerate(_iter_workbook_rows(path), start=1):
        if len(raw_row) < 5:
            continue
        try:
            code = _normalize_code(raw_row[3], field_name="code")
        except ValueError:
            continue
        if code is None:
            continue
        rows.append(
            AdministrativeDivisionSeedRow(
                name=str(raw_row[0]).strip(),
                division_type=str(raw_row[1]).strip(),
                level=int(str(raw_row[2]).strip()),
                code=code,
                adcode=code[:6],
                parent_code=_normalize_code(raw_row[4]),
                sort_order=sort_order,
            ),
        )
    return rows


def _iter_workbook_rows(path: Path) -> list[list[str]]:
    with ZipFile(path) as workbook:
        shared_strings = _read_shared_strings(workbook)
        worksheet_path = _resolve_first_worksheet_path(workbook)
        worksheet = ElementTree.fromstring(workbook.read(worksheet_path))
        sheet_data = worksheet.find("main:sheetData", _XML_NS)
        if sheet_data is None:
            return []

        rows: list[list[str]] = []
        for row in sheet_data.findall("main:row", _XML_NS):
            values: list[str] = []
            for cell in row.findall("main:c", _XML_NS):
                cell_type = cell.attrib.get("t")
                value_element = cell.find("main:v", _XML_NS)
                value = value_element.text if value_element is not None else ""
                if cell_type == "s" and value:
                    value = shared_strings[int(value)]
                values.append(value)
            rows.append(values)
        return rows[1:]


def _read_shared_strings(workbook: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in workbook.namelist():
        return []
    shared_strings: list[str] = []
    root = ElementTree.fromstring(workbook.read("xl/sharedStrings.xml"))
    for item in root.findall("main:si", _XML_NS):
        parts = [node.text or "" for node in item.iterfind(".//main:t", _XML_NS)]
        shared_strings.append("".join(parts))
    return shared_strings


def _resolve_first_worksheet_path(workbook: ZipFile) -> str:
    workbook_root = ElementTree.fromstring(workbook.read("xl/workbook.xml"))
    sheets = workbook_root.find("main:sheets", _XML_NS)
    if sheets is None or not list(sheets):
        raise ValueError("Administrative division workbook does not contain any worksheet.")
    first_sheet = list(sheets)[0]
    relationship_id = first_sheet.attrib.get(_REL_ID_ATTR)
    if not relationship_id:
        raise ValueError("Administrative division workbook sheet is missing relationship id.")

    relationships_root = ElementTree.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))
    target_by_id = {item.attrib["Id"]: item.attrib["Target"] for item in relationships_root}
    target = target_by_id[relationship_id]
    return target if target.startswith("xl/") else f"xl/{target}"


def _normalize_code(raw_value: object, *, field_name: str = "parent_code") -> str | None:
    normalized = str(raw_value or "").strip()
    if not normalized or normalized in {"-1", "000000000000"}:
        return None
    if not normalized.isdigit():
        raise ValueError(f"Administrative division {field_name} must be numeric.")
    return normalized
