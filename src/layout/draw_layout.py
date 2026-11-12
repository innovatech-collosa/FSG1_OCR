import cv2
def draw_layout_overlay(image,lines,cells,tokens):
    out=image.copy()
    for l in lines:
        b=l.bbox_px; color=(255,0,0) if l.orientation=="H" else (255,120,0); cv2.rectangle(out,(int(b.x0),int(b.y0)),(int(b.x1),int(b.y1)),color,2)
    for c in cells:
        b=c.bbox_px; cv2.rectangle(out,(int(b.x0),int(b.y0)),(int(b.x1),int(b.y1)),(0,0,255),2)
    for t in tokens:
        b=t.bbox_px; cv2.rectangle(out,(int(b.x0),int(b.y0)),(int(b.x1),int(b.y1)),(0,180,0),1)
    return out
