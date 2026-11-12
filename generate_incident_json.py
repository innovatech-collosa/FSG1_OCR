#!/usr/bin/env python3
from pathlib import Path
import argparse,json,yaml
from src.extraction.field_extractor import extract_fields
from src.extraction.clean_output import build_incident

def main():
    ap=argparse.ArgumentParser(description='FSG1_OCR V2.1.1 - genera JSON humano desde ocr.json')
    ap.add_argument('entrada',type=Path,help='ocr.json o carpeta output/<documento>')
    ap.add_argument('--output',type=Path)
    args=ap.parse_args(); src=args.entrada
    if src.is_dir():src=src/'ocr.json'
    if not src.exists():raise SystemExit(f'No existe: {src}')
    root=Path(__file__).resolve().parent
    defs=yaml.safe_load((root/'config/human_fields.yaml').read_text(encoding='utf-8'))['fields']
    ocr=json.loads(src.read_text(encoding='utf-8'))
    fields=extract_fields(ocr,defs)
    filename=ocr.get('document',{}).get('filename',src.stem)
    result=build_incident(fields,filename)
    out=args.output or src.parent/'incidente.json'
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'OK: {out}')
if __name__=='__main__':main()
