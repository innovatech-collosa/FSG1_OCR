from src.models.geometry import BoundingBox, normalize_bbox
from src.models.ocr import OCRLine

def build_lines(tokens,page_width:int,page_height:int):
    if not tokens:return []
    ordered=sorted(tokens,key=lambda t:(t.bbox_px.center_y,t.bbox_px.x0)); groups=[]
    for t in ordered:
        match=None
        for g in reversed(groups[-4:]):
            cy=sum(x.bbox_px.center_y for x in g)/len(g); mh=sum(x.bbox_px.height for x in g)/len(g)
            if abs(t.bbox_px.center_y-cy)<=max(6,.55*mh): match=g; break
        if match is None: groups.append([t])
        else: match.append(t)
    lines=[]
    for g in groups:
        g.sort(key=lambda t:t.bbox_px.x0)
        b=BoundingBox(min(t.bbox_px.x0 for t in g),min(t.bbox_px.y0 for t in g),max(t.bbox_px.x1 for t in g),max(t.bbox_px.y1 for t in g))
        lines.append(OCRLine(" ".join(t.text for t in g),g,b,normalize_bbox(b,page_width,page_height)))
    return lines
