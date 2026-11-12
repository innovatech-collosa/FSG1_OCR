#!/usr/bin/env python3
"""Compara dos informes generados por regression_contract.py."""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional

EXIT_PASS = 0
EXIT_REVIEW = 1
EXIT_FAIL = 2
EXIT_ERROR = 3

DEFAULT_METRICS = (
    "ocr.tokens",
    "ocr.tokens_in_cells",
    "ocr.tokens_outside_cells",
    "ocr.multi_cell_tokens",
    "geometry.lines",
    "geometry.horizontal_lines",
    "geometry.vertical_lines",
    "geometry.table_regions",
    "geometry.cells",
    "relations.total",
    "relations.nearest_right",
    "relations.nearest_below",
    "relations.right_null",
    "relations.below_null",
)

HARD_REGRESSION_CODES = {
    "DUPLICATE_ENTITY_ID",
    "NON_FINITE_BBOX",
    "INVALID_BBOX_ORDER",
    "TOKEN_COORDINATES_MODIFIED",
    "DANGLING_TOKEN_CELL_REFERENCE",
    "DANGLING_CELL_TABLE_REFERENCE",
    "DANGLING_CELL_TOKEN_REFERENCE",
    "DANGLING_TABLE_CELL_REFERENCE",
    "DANGLING_RELATION_SOURCE",
    "DANGLING_RELATION_TARGET",
    "TOKEN_ASSIGNED_TO_MULTIPLE_CELLS",
    "TABLE_CELL_ID_COLLISION",
    "SELF_RELATION",
    "CROSS_PAGE_NEIGHBOUR",
    "INVALID_RIGHT_DIRECTION",
    "INVALID_BELOW_DIRECTION",
}


@dataclass
class MetricDelta:
    metric: str
    baseline: float
    candidate: float
    absolute_delta: float
    percent_delta: Optional[float]
    status: str
    reason: str = ""


@dataclass
class ComparisonReport:
    schema_version: str
    baseline_file: str
    candidate_file: str
    baseline_version: str
    candidate_version: str
    status: str
    review_threshold_percent: float
    metrics: list[MetricDelta] = field(default_factory=list)
    blocking_regressions: list[dict[str, Any]] = field(default_factory=list)
    new_findings: list[dict[str, Any]] = field(default_factory=list)
    resolved_findings: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)


def get_path(data: Mapping[str, Any], dotted_path: str) -> Any:
    current: Any = data
    for part in dotted_path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            raise KeyError(dotted_path)
        current = current[part]
    return current


def percentage_delta(baseline: float, candidate: float) -> Optional[float]:
    if math.isclose(baseline, 0.0):
        return 0.0 if math.isclose(candidate, 0.0) else None
    return ((candidate - baseline) / abs(baseline)) * 100.0


def finding_signature(finding: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        finding.get("code"),
        finding.get("severity"),
        tuple(sorted(map(str, finding.get("entity_ids", [])))),
    )


def compare_findings(
    baseline: Mapping[str, Any], candidate: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    baseline_findings = baseline.get("findings", [])
    candidate_findings = candidate.get("findings", [])
    if not isinstance(baseline_findings, list) or not isinstance(candidate_findings, list):
        raise ValueError("El campo findings debe ser una lista.")

    baseline_map = {
        finding_signature(finding): dict(finding)
        for finding in baseline_findings
        if isinstance(finding, Mapping)
    }
    candidate_map = {
        finding_signature(finding): dict(finding)
        for finding in candidate_findings
        if isinstance(finding, Mapping)
    }

    new_keys = sorted(candidate_map.keys() - baseline_map.keys(), key=repr)
    resolved_keys = sorted(baseline_map.keys() - candidate_map.keys(), key=repr)
    return (
        [candidate_map[signature] for signature in new_keys],
        [baseline_map[signature] for signature in resolved_keys],
    )


class VersionComparator:
    def __init__(self, review_threshold_percent: float = 25.0) -> None:
        if review_threshold_percent < 0:
            raise ValueError("El umbral de revision no puede ser negativo.")
        self.review_threshold_percent = review_threshold_percent

    def compare(
        self,
        baseline: Mapping[str, Any],
        candidate: Mapping[str, Any],
        baseline_file: str,
        candidate_file: str,
    ) -> ComparisonReport:
        self._validate_report(baseline, "baseline")
        self._validate_report(candidate, "candidate")

        metric_deltas = self._compare_metrics(baseline["metrics"], candidate["metrics"])
        new_findings, resolved_findings = compare_findings(baseline, candidate)
        blockers = self._blocking_regressions(baseline, candidate, new_findings)
        status = self._resolve_status(candidate, metric_deltas, blockers, new_findings)

        summary = {
            "metrics_compared": len(metric_deltas),
            "metrics_pass": sum(delta.status == "PASS" for delta in metric_deltas),
            "metrics_review": sum(delta.status == "REVIEW" for delta in metric_deltas),
            "metrics_fail": sum(delta.status == "FAIL" for delta in metric_deltas),
            "new_findings": len(new_findings),
            "resolved_findings": len(resolved_findings),
            "blocking_regressions": len(blockers),
            "structure_changed": baseline.get("deterministic_hash") != candidate.get("deterministic_hash"),
        }

        return ComparisonReport(
            schema_version="1.0",
            baseline_file=baseline_file,
            candidate_file=candidate_file,
            baseline_version=str(baseline.get("document_version", "unknown")),
            candidate_version=str(candidate.get("document_version", "unknown")),
            status=status,
            review_threshold_percent=self.review_threshold_percent,
            metrics=metric_deltas,
            blocking_regressions=blockers,
            new_findings=new_findings,
            resolved_findings=resolved_findings,
            summary=summary,
        )

    @staticmethod
    def _validate_report(report: Mapping[str, Any], label: str) -> None:
        if "metrics" not in report or not isinstance(report["metrics"], Mapping):
            raise ValueError(f"El informe {label} no contiene metrics validas.")
        if "status" not in report:
            raise ValueError(f"El informe {label} no contiene status.")

    def _compare_metrics(
        self,
        baseline_metrics: Mapping[str, Any],
        candidate_metrics: Mapping[str, Any],
    ) -> list[MetricDelta]:
        result: list[MetricDelta] = []
        for metric in DEFAULT_METRICS:
            try:
                baseline_value = float(get_path(baseline_metrics, metric))
                candidate_value = float(get_path(candidate_metrics, metric))
            except (KeyError, TypeError, ValueError):
                continue

            absolute = candidate_value - baseline_value
            percent = percentage_delta(baseline_value, candidate_value)
            status = "PASS"
            reason = ""

            if metric == "ocr.tokens" and candidate_value < baseline_value:
                status = "FAIL"
                reason = "La version candidata pierde tokens OCR."
            elif metric == "ocr.multi_cell_tokens" and candidate_value > baseline_value:
                status = "FAIL"
                reason = "Aumentan los tokens asignados a varias celdas."

            if status != "FAIL":
                if percent is None:
                    status = "REVIEW"
                    reason = "El baseline era cero y la metrica deja de serlo."
                elif abs(percent) >= self.review_threshold_percent and not math.isclose(percent, 0.0):
                    status = "REVIEW"
                    reason = "La variacion supera el umbral estructural."

            result.append(
                MetricDelta(
                    metric=metric,
                    baseline=baseline_value,
                    candidate=candidate_value,
                    absolute_delta=absolute,
                    percent_delta=percent,
                    status=status,
                    reason=reason,
                )
            )
        return result

    @staticmethod
    def _blocking_regressions(
        baseline: Mapping[str, Any],
        candidate: Mapping[str, Any],
        new_findings: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        blockers: list[dict[str, Any]] = []
        baseline_tokens = get_path(baseline["metrics"], "ocr.tokens")
        candidate_tokens = get_path(candidate["metrics"], "ocr.tokens")

        if candidate_tokens < baseline_tokens:
            blockers.append(
                {
                    "code": "OCR_TOKEN_LOSS",
                    "message": f"Los tokens bajan de {baseline_tokens} a {candidate_tokens}.",
                }
            )

        for finding in new_findings:
            code = finding.get("code")
            severity = finding.get("severity")
            if severity == "ERROR" or code in HARD_REGRESSION_CODES:
                blockers.append(
                    {
                        "code": code,
                        "message": finding.get("message", ""),
                        "entity_ids": finding.get("entity_ids", []),
                    }
                )

        if candidate.get("status") == "FAIL":
            blockers.append(
                {
                    "code": "CANDIDATE_CONTRACT_FAILED",
                    "message": "La version candidata incumple su contrato individual.",
                }
            )
        return blockers

    @staticmethod
    def _resolve_status(
        candidate: Mapping[str, Any],
        metric_deltas: list[MetricDelta],
        blockers: list[dict[str, Any]],
        new_findings: list[dict[str, Any]],
    ) -> str:
        if blockers or candidate.get("status") == "FAIL":
            return "FAIL"
        if any(delta.status == "FAIL" for delta in metric_deltas):
            return "FAIL"
        if candidate.get("status") == "REVIEW":
            return "REVIEW"
        if any(delta.status == "REVIEW" for delta in metric_deltas):
            return "REVIEW"
        if new_findings:
            return "REVIEW"
        return "PASS"


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"El archivo {path} no contiene un objeto JSON raiz.")
    return data


def comparison_to_dict(report: ComparisonReport) -> dict[str, Any]:
    return asdict(report)


def print_console_report(report: ComparisonReport) -> None:
    print()
    print("FSG1 V2.1.x REGRESSION COMPARISON")
    print("=" * 78)
    print(f"Baseline:  {report.baseline_version} ({report.baseline_file})")
    print(f"Candidate: {report.candidate_version} ({report.candidate_file})")
    print(f"Result:    {report.status}")
    print()

    header = f"{'METRIC':34}{'BASE':>10}{'CAND':>10}{'DELTA %':>13}{'STATE':>11}"
    print(header)
    print("-" * len(header))
    for delta in report.metrics:
        percent_text = "n/a" if delta.percent_delta is None else f"{delta.percent_delta:+.2f}%"
        print(
            f"{delta.metric:34}"
            f"{delta.baseline:10.0f}"
            f"{delta.candidate:10.0f}"
            f"{percent_text:>13}"
            f"{delta.status:>11}"
        )

    if report.blocking_regressions:
        print()
        print("BLOCKING REGRESSIONS")
        print("-" * 78)
        for blocker in report.blocking_regressions:
            print(f"- {blocker.get('code')}: {blocker.get('message', '')}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compara dos informes de contrato FSG1 V2.1.x.")
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--review-threshold", type=float, default=25.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        baseline = load_json(args.baseline)
        candidate = load_json(args.candidate)
        comparator = VersionComparator(args.review_threshold)
        report = comparator.compare(
            baseline,
            candidate,
            str(args.baseline),
            str(args.candidate),
        )
        output = args.output or Path(
            f"comparison_{report.baseline_version}_vs_{report.candidate_version}.json"
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(comparison_to_dict(report), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print_console_report(report)
        print()
        print(f"Detailed report: {output}")
        return {"PASS": EXIT_PASS, "REVIEW": EXIT_REVIEW, "FAIL": EXIT_FAIL}[report.status]
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
