from pathlib import Path
import json, cv2
from src.rendering.pdf_renderer import render_pdf
from src.preprocessing.image_variants import create_variants
from src.ocr.line_builder import build_lines
from src.diagnostics.draw_ocr import draw_ocr_overlay
from src.diagnostics.report import build_report
from src.layout.line_detector import detect_lines
from src.layout.cell_detector import detect_cells, assign_tokens_to_cells
from src.layout.spatial_graph import build_relations
from src.layout.draw_layout import draw_layout_overlay

def process_document(pdf_path:Path,output_root:Path,config:dict,ocr_engine):
    target=output_root/pdf_path.stem; pages_dir=target/"pages"; diag_dir=target/"diagnostic"
    pages_dir.mkdir(parents=True,exist_ok=True); diag_dir.mkdir(parents=True,exist_ok=True)
    rows=[]; layout_rows=[]; all_tokens=[]
    pages=render_pdf(pdf_path,int(config["rendering"].get("dpi",300)))
    for p in pages:
        v=create_variants(p.image,config.get("preprocessing",{})); n=p.info.number
        cv2.imwrite(str(pages_dir/f"page_{n:03d}_original.png"),v.original)
        cv2.imwrite(str(pages_dir/f"page_{n:03d}_ocr.png"),v.ocr)
        cv2.imwrite(str(pages_dir/f"page_{n:03d}_binary.png"),v.binary)
        tokens=ocr_engine.recognize(v.ocr,n); lines=build_lines(tokens,p.info.width,p.info.height); all_tokens.append(tokens)
        cv2.imwrite(str(diag_dir/f"page_{n:03d}_ocr_overlay.png"),draw_ocr_overlay(v.ocr,tokens))
        lines_geom, hmask, vmask = detect_lines(v.binary, config.get("layout", {}))
        cells = assign_tokens_to_cells(tokens, detect_cells(hmask, vmask, p.info.width, p.info.height, config.get("layout", {})))
        relations = build_relations(tokens)
        cv2.imwrite(str(diag_dir/f"page_{n:03d}_layout_overlay.png"), draw_layout_overlay(v.ocr, lines_geom, cells, tokens))
        layout_rows.append({"page":n,"lines":[x.to_dict() for x in lines_geom],"cells":[x.to_dict() for x in cells],"relations":[x.to_dict() for x in relations]})
        rows.append({"page":n,"width":p.info.width,"height":p.info.height,"dpi":p.info.dpi,"tokens":[t.to_dict() for t in tokens],"lines":[l.to_dict() for l in lines]})
    payload={"schema":"FSG1_OCR","version":str(config.get("version","2.0.0")),"document":{"filename":pdf_path.name,"pages":len(rows)},"pages":rows}
    (target/"ocr.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    layout_payload={"schema":"FSG1_LAYOUT","version":str(config.get("version","2.1.0")),"document":{"filename":pdf_path.name,"pages":len(layout_rows)},"pages":layout_rows}
    (target/"layout.json").write_text(json.dumps(layout_payload,ensure_ascii=False,indent=2),encoding="utf-8")
    report=build_report(pdf_path.name,all_tokens); (target/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    return target
