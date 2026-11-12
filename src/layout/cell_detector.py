import cv2
from src.models.geometry import BoundingBox, normalize_bbox
from .models import Cell

def detect_cells(horizontal_mask,vertical_mask,width,height,config):
    grid=cv2.bitwise_or(horizontal_mask,vertical_mask)
    contours,_=cv2.findContours(grid,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
    minw=width*float(config.get("min_cell_width_ratio",.018)); minh=height*float(config.get("min_cell_height_ratio",.008))
    boxes=[]
    for c in contours:
        x,y,w,h=cv2.boundingRect(c)
        if w<minw or h<minh or w>width*.995 or h>height*.90: continue
        boxes.append((x,y,w,h))
    # dedupe near-identical nested contours
    boxes.sort(key=lambda z:z[2]*z[3],reverse=True); kept=[]
    for b in boxes:
        x,y,w,h=b
        if any(abs(x-a[0])<=2 and abs(y-a[1])<=2 and abs(x+w-(a[0]+a[2]))<=3 and abs(y+h-(a[1]+a[3]))<=3 for a in kept): continue
        kept.append(b)
    kept=kept[:int(config.get("max_cells_per_page",1200))]
    cells=[]
    for i,(x,y,w,h) in enumerate(sorted(kept,key=lambda z:(z[1],z[0]))):
        box=BoundingBox(float(x),float(y),float(x+w),float(y+h)); cells.append(Cell(f"cell_{i:04d}",box,normalize_bbox(box,width,height),[]))
    return cells

def assign_tokens_to_cells(tokens,cells):
    for i,t in enumerate(tokens):
        cx,cy=t.bbox_px.center_x,t.bbox_px.center_y
        candidates=[c for c in cells if c.bbox_px.x0<=cx<=c.bbox_px.x1 and c.bbox_px.y0<=cy<=c.bbox_px.y1]
        if candidates: min(candidates,key=lambda c:c.bbox_px.width*c.bbox_px.height).token_indexes.append(i)
    return cells
