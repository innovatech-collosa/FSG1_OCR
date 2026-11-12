#!/usr/bin/env python3
"""Contrato de regresion para la capa estructural de FSG1 V2.1.x."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

EXIT_PASS = 0
EXIT_REVIEW = 1
EXIT_FAIL = 2
EXIT_ERROR = 3

DUPLICATE_IOU_THRESHOLD = 0.90
DUPLICATE_AREA_RATIO_THRESHOLD = 0.90
GEOMETRY_EPSILON = 1e-6


@dataclass(frozen=True)
class BBox:
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def width(self) -> float:
        return max(0.0, self.x2 - self.x1)

    @property
    def height(self) -> float:
        return max(0.0, self.y2 - self.y1)

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center_x(self) -> float:
        return (self.x1 + self.x2) / 2.0

    @property
    def center_y(self) -> float:
        return (self.y1 + self.y2) / 2.0

    def as_list(self) -> list[float]:
        return [self.x1, self.y1, self.x2, self.y2]


@dataclass
class Token:
    id: str
    bbox: BBox
    text: str = ""
    cell_id: Optional[str] = None
    page: int = 0
    original_bbox: Optional[BBox] = None


@dataclass
class Line:
    id: str
    bbox: BBox
    orientation: str
    page: int = 0
    validated: bool = True


@dataclass
class Cell:
    id: str
    bbox: BBox
    token_ids: list[str] = field(default_factory=list)
    table_region_id: Optional[str] = None
    page: int = 0


@dataclass
class TableRegion:
    id: str
    bbox: BBox
    cell_ids: list[str] = field(default_factory=list)
    page: int = 0


@dataclass
class Relation:
    source_id: str
    target_id: Optional[str]
    relation_type: str
    confidence: Optional[float] = None
    page: int = 0


@dataclass
class NormalizedDocument:
    tokens: list[Token]
    lines: list[Line]
    cells: list[Cell]
    table_regions: list[TableRegion]
    relations: list[Relation]
    source_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Finding:
    code: str
    severity: str
    message: str
    entity_ids: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ContractReport:
    schema_version: str
    source_file: str
    document_version: str
    status: str
    deterministic_hash: str
    metrics: dict[str, Any]
    findings: list[Finding]
    contract: dict[str, Any]


class StructureAdapter:
    """Adapta variantes del JSON FSG1 a un modelo interno estable."""

    TOKEN_KEYS = ("tokens", "ocr_tokens", "words")
    LINE_KEYS = ("lines", "geometric_lines")
    CELL_KEYS = ("cells", "table_cells")
    TABLE_KEYS = ("table_regions", "tables")
    RELATION_KEYS = ("relations", "spatial_relations")

    def normalize(self, raw: Mapping[str, Any]) -> NormalizedDocument:
        root = raw.get("structure", raw)
        if not isinstance(root, Mapping):
            raise ValueError("El nodo raiz/structure debe ser un objeto JSON.")

        tokens = [
            self._token(item, index)
            for index, item in enumerate(self._collection(root, self.TOKEN_KEYS))
        ]
        lines = [
            self._line(item, index)
            for index, item in enumerate(self._collection(root, self.LINE_KEYS))
        ]
        cells = [
            self._cell(item, index)
            for index, item in enumerate(self._collection(root, self.CELL_KEYS))
        ]
        tables = [
            self._table(item, index)
            for index, item in enumerate(self._collection(root, self.TABLE_KEYS))
        ]
        relations = [
            self._relation(item)
            for item in self._collection(root, self.RELATION_KEYS)
        ]

        metadata = raw.get("metadata", {})
        if not isinstance(metadata, Mapping):
            metadata = {}

        return NormalizedDocument(
            tokens=tokens,
            lines=lines,
            cells=cells,
            table_regions=tables,
            relations=relations,
            source_metadata=dict(metadata),
        )

    @staticmethod
    def _collection(
        root: Mapping[str, Any], possible_keys: Sequence[str]
    ) -> list[Mapping[str, Any]]:
        for key in possible_keys:
            value = root.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, Mapping)]
        return []

    def _token(self, item: Mapping[str, Any], index: int) -> Token:
        original = item.get("original_bbox")
        return Token(
            id=str(item.get("id", f"token_{index:06d}")),
            bbox=self._bbox(item),
            original_bbox=self._bbox_value(original) if original is not None else None,
            text=str(item.get("text", "")),
            cell_id=self._optional_string(item.get("cell_id", item.get("cell"))),
            page=int(item.get("page", item.get("page_index", 0))),
        )

    def _line(self, item: Mapping[str, Any], index: int) -> Line:
        orientation = str(item.get("orientation", item.get("type", "unknown"))).lower()
        aliases = {
            "h": "horizontal",
            "horizontal_line": "horizontal",
            "v": "vertical",
            "vertical_line": "vertical",
        }
        return Line(
            id=str(item.get("id", f"line_{index:06d}")),
            bbox=self._bbox(item),
            orientation=aliases.get(orientation, orientation),
            page=int(item.get("page", item.get("page_index", 0))),
            validated=bool(item.get("validated", True)),
        )

    def _cell(self, item: Mapping[str, Any], index: int) -> Cell:
        return Cell(
            id=str(item.get("id", f"cell_{index:06d}")),
            bbox=self._bbox(item),
            token_ids=self._reference_ids(item.get("token_ids", item.get("tokens", []))),
            table_region_id=self._optional_string(
                item.get("table_region_id", item.get("table_id"))
            ),
            page=int(item.get("page", item.get("page_index", 0))),
        )

    def _table(self, item: Mapping[str, Any], index: int) -> TableRegion:
        return TableRegion(
            id=str(item.get("id", f"table_{index:06d}")),
            bbox=self._bbox(item),
            cell_ids=self._reference_ids(item.get("cell_ids", item.get("cells", []))),
            page=int(item.get("page", item.get("page_index", 0))),
        )

    def _relation(self, item: Mapping[str, Any]) -> Relation:
        return Relation(
            source_id=str(item.get("source_id", item.get("source", ""))),
            target_id=self._optional_string(item.get("target_id", item.get("target"))),
            relation_type=str(
                item.get("relation_type", item.get("type", ""))
            ).upper(),
            confidence=self._optional_float(item.get("confidence")),
            page=int(item.get("page", item.get("page_index", 0))),
        )

    def _bbox(self, item: Mapping[str, Any]) -> BBox:
        for key in ("bbox", "box", "rect"):
            if key in item:
                return self._bbox_value(item[key])

        if all(key in item for key in ("x", "y", "width", "height")):
            x = float(item["x"])
            y = float(item["y"])
            return BBox(x, y, x + float(item["width"]), y + float(item["height"]))

        if all(key in item for key in ("x1", "y1", "x2", "y2")):
            return BBox(
                float(item["x1"]),
                float(item["y1"]),
                float(item["x2"]),
                float(item["y2"]),
            )

        raise ValueError(f"No se ha encontrado bbox en: {item}")

    @staticmethod
    def _bbox_value(value: Any) -> BBox:
        if isinstance(value, Mapping):
            if all(key in value for key in ("x1", "y1", "x2", "y2")):
                return BBox(
                    float(value["x1"]),
                    float(value["y1"]),
                    float(value["x2"]),
                    float(value["y2"]),
                )
            if all(key in value for key in ("x", "y", "width", "height")):
                x = float(value["x"])
                y = float(value["y"])
                return BBox(
                    x,
                    y,
                    x + float(value["width"]),
                    y + float(value["height"]),
                )

        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and len(value) == 4:
            x1, y1, x2, y2 = map(float, value)
            return BBox(x1, y1, x2, y2)

        raise ValueError(f"Formato bbox no admitido: {value!r}")

    @staticmethod
    def _reference_ids(values: Any) -> list[str]:
        if not isinstance(values, list):
            return []
        result: list[str] = []
        for value in values:
            if isinstance(value, Mapping):
                reference = value.get("id")
                if reference is not None:
                    result.append(str(reference))
            elif value is not None:
                result.append(str(value))
        return result

    @staticmethod
    def _optional_string(value: Any) -> Optional[str]:
        return None if value is None else str(value)

    @staticmethod
    def _optional_float(value: Any) -> Optional[float]:
        return None if value is None else float(value)


class RegressionContract:
    def __init__(
        self,
        duplicate_iou: float = DUPLICATE_IOU_THRESHOLD,
        duplicate_area_ratio: float = DUPLICATE_AREA_RATIO_THRESHOLD,
    ) -> None:
        self.duplicate_iou = duplicate_iou
        self.duplicate_area_ratio = duplicate_area_ratio
        self.findings: list[Finding] = []

    def evaluate(
        self,
        document: NormalizedDocument,
        source_file: str,
        document_version: str,
    ) -> ContractReport:
        self.findings = []
        self._validate_unique_ids(document)
        self._validate_bboxes(document)
        self._validate_coordinate_preservation(document)
        self._validate_references(document)
        self._validate_token_assignments(document)
        self._validate_table_cell_separation(document)
        self._validate_duplicate_cells(document)
        self._validate_relations(document)
        self._validate_table_evidence(document)

        metrics = self._calculate_metrics(document)
        return ContractReport(
            schema_version="1.0",
            source_file=source_file,
            document_version=document_version,
            status=self._resolve_status(),
            deterministic_hash=self._deterministic_hash(document),
            metrics=metrics,
            findings=self.findings,
            contract={
                "duplicate_iou_threshold": self.duplicate_iou,
                "duplicate_area_ratio_threshold": self.duplicate_area_ratio,
            },
        )

    def _error(self, code: str, message: str, entity_ids: Optional[list[str]] = None, **details: Any) -> None:
        self.findings.append(Finding(code, "ERROR", message, entity_ids or [], details))

    def _warning(self, code: str, message: str, entity_ids: Optional[list[str]] = None, **details: Any) -> None:
        self.findings.append(Finding(code, "WARNING", message, entity_ids or [], details))

    @staticmethod
    def _all_entities(document: NormalizedDocument) -> list[Any]:
        return [*document.tokens, *document.lines, *document.cells, *document.table_regions]

    def _validate_unique_ids(self, document: NormalizedDocument) -> None:
        counts = Counter(entity.id for entity in self._all_entities(document))
        for entity_id, count in counts.items():
            if count > 1:
                self._error(
                    "DUPLICATE_ENTITY_ID",
                    f"El ID {entity_id!r} aparece {count} veces.",
                    [entity_id],
                    count=count,
                )

    def _validate_bboxes(self, document: NormalizedDocument) -> None:
        for entity in self._all_entities(document):
            bbox = entity.bbox
            values = (bbox.x1, bbox.y1, bbox.x2, bbox.y2)
            if not all(math.isfinite(value) for value in values):
                self._error("NON_FINITE_BBOX", "Coordenadas no finitas.", [entity.id], bbox=bbox.as_list())
                continue
            if bbox.x2 < bbox.x1 or bbox.y2 < bbox.y1:
                self._error("INVALID_BBOX_ORDER", "BBox con extremos invertidos.", [entity.id], bbox=bbox.as_list())
            if bbox.area <= GEOMETRY_EPSILON:
                self._warning("ZERO_AREA_BBOX", "BBox de area nula.", [entity.id], bbox=bbox.as_list())

    def _validate_coordinate_preservation(self, document: NormalizedDocument) -> None:
        for token in document.tokens:
            if token.original_bbox is not None and token.bbox != token.original_bbox:
                self._error(
                    "TOKEN_COORDINATES_MODIFIED",
                    "Las coordenadas OCR originales fueron modificadas.",
                    [token.id],
                    original=token.original_bbox.as_list(),
                    current=token.bbox.as_list(),
                )

    def _validate_references(self, document: NormalizedDocument) -> None:
        token_ids = {token.id for token in document.tokens}
        cell_ids = {cell.id for cell in document.cells}
        table_ids = {table.id for table in document.table_regions}
        node_ids = token_ids | cell_ids | table_ids

        for token in document.tokens:
            if token.cell_id is not None and token.cell_id not in cell_ids:
                self._error("DANGLING_TOKEN_CELL_REFERENCE", "Token referencia celda inexistente.", [token.id, token.cell_id])

        for cell in document.cells:
            if cell.table_region_id is not None and cell.table_region_id not in table_ids:
                self._error("DANGLING_CELL_TABLE_REFERENCE", "Celda referencia TableRegion inexistente.", [cell.id, cell.table_region_id])
            for token_id in cell.token_ids:
                if token_id not in token_ids:
                    self._error("DANGLING_CELL_TOKEN_REFERENCE", "Celda referencia token inexistente.", [cell.id, token_id])

        for table in document.table_regions:
            for cell_id in table.cell_ids:
                if cell_id not in cell_ids:
                    self._error("DANGLING_TABLE_CELL_REFERENCE", "TableRegion referencia celda inexistente.", [table.id, cell_id])

        for relation in document.relations:
            if relation.source_id not in node_ids:
                self._error("DANGLING_RELATION_SOURCE", "Origen de relacion inexistente.", [relation.source_id])
            if relation.target_id is not None and relation.target_id not in node_ids:
                self._error("DANGLING_RELATION_TARGET", "Destino de relacion inexistente.", [relation.target_id])

    def _validate_token_assignments(self, document: NormalizedDocument) -> None:
        assignments: defaultdict[str, set[str]] = defaultdict(set)
        for cell in document.cells:
            for token_id in cell.token_ids:
                assignments[token_id].add(cell.id)
        for token in document.tokens:
            if token.cell_id:
                assignments[token.id].add(token.cell_id)
        for token_id, cell_ids in assignments.items():
            if len(cell_ids) > 1:
                self._error(
                    "TOKEN_ASSIGNED_TO_MULTIPLE_CELLS",
                    "El token esta asignado a varias celdas.",
                    [token_id, *sorted(cell_ids)],
                )

    def _validate_table_cell_separation(self, document: NormalizedDocument) -> None:
        table_ids = {table.id for table in document.table_regions}
        cell_ids = {cell.id for cell in document.cells}
        for entity_id in table_ids & cell_ids:
            self._error("TABLE_CELL_ID_COLLISION", "TableRegion y Cell comparten ID.", [entity_id])

        for table in document.table_regions:
            for cell in document.cells:
                if table.page == cell.page and table.bbox == cell.bbox and len(table.cell_ids) > 1:
                    self._warning(
                        "TABLE_EQUIVALENT_TO_CHILD_CELL",
                        "Una celda replica integramente el contenedor.",
                        [table.id, cell.id],
                    )

    def _validate_duplicate_cells(self, document: NormalizedDocument) -> None:
        cells_by_page: defaultdict[int, list[Cell]] = defaultdict(list)
        for cell in document.cells:
            cells_by_page[cell.page].append(cell)

        for page_cells in cells_by_page.values():
            for index, first in enumerate(page_cells):
                for second in page_cells[index + 1:]:
                    overlap = iou(first.bbox, second.bbox)
                    similarity = area_ratio(first.bbox, second.bbox)
                    if overlap >= self.duplicate_iou and similarity >= self.duplicate_area_ratio:
                        self._warning(
                            "POSSIBLE_DUPLICATE_CELL",
                            "Dos celdas presentan geometria equivalente.",
                            [first.id, second.id],
                            iou=round(overlap, 6),
                            area_ratio=round(similarity, 6),
                        )

    def _validate_relations(self, document: NormalizedDocument) -> None:
        nodes = {
            entity.id: entity
            for entity in [*document.tokens, *document.cells, *document.table_regions]
        }
        for relation in document.relations:
            if relation.target_id is None:
                continue
            if relation.source_id == relation.target_id:
                self._error("SELF_RELATION", "Una entidad no puede ser su propio vecino.", [relation.source_id], relation_type=relation.relation_type)
                continue
            source = nodes.get(relation.source_id)
            target = nodes.get(relation.target_id)
            if source is None or target is None:
                continue
            if source.page != target.page:
                self._error("CROSS_PAGE_NEIGHBOUR", "Relacion espacial entre paginas distintas.", [source.id, target.id])
                continue
            if relation.relation_type == "NEAREST_RIGHT" and target.bbox.center_x <= source.bbox.center_x:
                self._error("INVALID_RIGHT_DIRECTION", "El destino no esta a la derecha.", [source.id, target.id])
            elif relation.relation_type == "NEAREST_BELOW" and target.bbox.center_y <= source.bbox.center_y:
                self._error("INVALID_BELOW_DIRECTION", "El destino no esta debajo.", [source.id, target.id])

    def _validate_table_evidence(self, document: NormalizedDocument) -> None:
        cells_by_table: defaultdict[str, list[Cell]] = defaultdict(list)
        for cell in document.cells:
            if cell.table_region_id:
                cells_by_table[cell.table_region_id].append(cell)
        for table in document.table_regions:
            associated = set(table.cell_ids)
            associated.update(cell.id for cell in cells_by_table.get(table.id, []))
            if not associated:
                self._warning("TABLE_WITHOUT_CELLS", "TableRegion sin celdas funcionales.", [table.id])

    def _calculate_metrics(self, document: NormalizedDocument) -> dict[str, Any]:
        horizontal_lines = sum(line.orientation == "horizontal" for line in document.lines)
        vertical_lines = sum(line.orientation == "vertical" for line in document.lines)
        assignments: defaultdict[str, set[str]] = defaultdict(set)
        for cell in document.cells:
            for token_id in cell.token_ids:
                assignments[token_id].add(cell.id)
        for token in document.tokens:
            if token.cell_id:
                assignments[token.id].add(token.cell_id)

        known_token_ids = {token.id for token in document.tokens}
        assigned_tokens = {
            token_id for token_id, cell_ids in assignments.items()
            if cell_ids and token_id in known_token_ids
        }
        relation_counts = Counter(
            relation.relation_type for relation in document.relations
            if relation.target_id is not None
        )
        null_relation_counts = Counter(
            relation.relation_type for relation in document.relations
            if relation.target_id is None
        )
        finding_counts = Counter(finding.severity for finding in self.findings)
        finding_codes = Counter(finding.code for finding in self.findings)

        return {
            "ocr": {
                "tokens": len(document.tokens),
                "tokens_in_cells": len(assigned_tokens),
                "tokens_outside_cells": len(document.tokens) - len(assigned_tokens),
                "multi_cell_tokens": sum(len(cell_ids) > 1 for cell_ids in assignments.values()),
            },
            "geometry": {
                "lines": len(document.lines),
                "horizontal_lines": horizontal_lines,
                "vertical_lines": vertical_lines,
                "unknown_orientation_lines": len(document.lines) - horizontal_lines - vertical_lines,
                "table_regions": len(document.table_regions),
                "cells": len(document.cells),
            },
            "relations": {
                "total": len(document.relations),
                "nearest_right": relation_counts["NEAREST_RIGHT"],
                "nearest_below": relation_counts["NEAREST_BELOW"],
                "right_null": null_relation_counts["NEAREST_RIGHT"],
                "below_null": null_relation_counts["NEAREST_BELOW"],
            },
            "validation": {
                "errors": finding_counts["ERROR"],
                "warnings": finding_counts["WARNING"],
                "finding_codes": dict(sorted(finding_codes.items())),
            },
        }

    @staticmethod
    def _deterministic_hash(document: NormalizedDocument) -> str:
        canonical = {
            "tokens": sorted(
                (t.id, t.bbox.as_list(), t.text, t.cell_id or "", t.page)
                for t in document.tokens
            ),
            "lines": sorted(
                (line.id, line.bbox.as_list(), line.orientation, line.page, line.validated)
                for line in document.lines
            ),
            "cells": sorted(
                (c.id, c.bbox.as_list(), sorted(c.token_ids), c.table_region_id or "", c.page)
                for c in document.cells
            ),
            "table_regions": sorted(
                (table.id, table.bbox.as_list(), sorted(table.cell_ids), table.page)
                for table in document.table_regions
            ),
            "relations": sorted(
                (
                    relation.source_id,
                    relation.target_id or "",
                    relation.relation_type,
                    relation.confidence if relation.confidence is not None else -1.0,
                    relation.page,
                )
                for relation in document.relations
            ),
        }
        serialized = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _resolve_status(self) -> str:
        severities = {finding.severity for finding in self.findings}
        if "ERROR" in severities:
            return "FAIL"
        if "WARNING" in severities:
            return "REVIEW"
        return "PASS"


def intersection_area(first: BBox, second: BBox) -> float:
    width = max(0.0, min(first.x2, second.x2) - max(first.x1, second.x1))
    height = max(0.0, min(first.y2, second.y2) - max(first.y1, second.y1))
    return width * height


def iou(first: BBox, second: BBox) -> float:
    intersection = intersection_area(first, second)
    union = first.area + second.area - intersection
    return 0.0 if union <= GEOMETRY_EPSILON else intersection / union


def area_ratio(first: BBox, second: BBox) -> float:
    largest = max(first.area, second.area)
    smallest = min(first.area, second.area)
    return 0.0 if largest <= GEOMETRY_EPSILON else smallest / largest


def report_to_dict(report: ContractReport) -> dict[str, Any]:
    return asdict(report)


def write_json(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Valida el contrato de regresion FSG1 V2.1.x.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--duplicate-iou", type=float, default=DUPLICATE_IOU_THRESHOLD)
    parser.add_argument("--duplicate-area-ratio", type=float, default=DUPLICATE_AREA_RATIO_THRESHOLD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        raw = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(raw, Mapping):
            raise ValueError("El JSON raiz debe ser un objeto.")
        document = StructureAdapter().normalize(raw)
        contract = RegressionContract(args.duplicate_iou, args.duplicate_area_ratio)
        report = contract.evaluate(document, str(args.input), args.version)
        output = args.output or args.input.with_name(f"{args.input.stem}_contract.json")
        write_json(output, report_to_dict(report))
        print(f"Contract status: {report.status}")
        print(f"Errors: {report.metrics['validation']['errors']}")
        print(f"Warnings: {report.metrics['validation']['warnings']}")
        print(f"Report: {output}")
        return {"PASS": EXIT_PASS, "REVIEW": EXIT_REVIEW, "FAIL": EXIT_FAIL}[report.status]
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
