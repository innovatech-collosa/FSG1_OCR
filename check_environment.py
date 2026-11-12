import json
from src.ocr.version_check import compatibility_report

if __name__ == "__main__":
    report = compatibility_report()
    print(json.dumps(report, indent=2, ensure_ascii=False))
    raise SystemExit(0 if report["compatible"] else 1)
