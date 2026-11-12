from pathlib import Path
import argparse, yaml
from src.ocr.paddle_engine import PaddleOCREngine
from src.pipeline.document_pipeline import process_document

def discover(path:Path):
    if path.is_file(): return [path] if path.suffix.lower()==".pdf" else []
    return sorted(path.glob("*.pdf"))

def main():
    root=Path(__file__).resolve().parent
    ap=argparse.ArgumentParser(description="FSG1_OCR V2.1.0 - OCR visual neutro")
    ap.add_argument("entrada",nargs="?",type=Path,default=root/"input")
    ap.add_argument("--output",type=Path,default=root/"output")
    args=ap.parse_args()
    cfg=yaml.safe_load((root/"config/settings.yaml").read_text(encoding="utf-8"))
    engine=PaddleOCREngine.from_config(cfg["ocr"])
    pdfs=discover(args.entrada.expanduser().resolve())
    if not pdfs: raise SystemExit(f"No se encontraron PDF en: {args.entrada}")
    for pdf in pdfs:
        out=process_document(pdf,args.output.expanduser().resolve(),cfg,engine); print(f"OK: {pdf.name} -> {out}")
if __name__=="__main__": main()
