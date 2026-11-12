import cv2, numpy as np
from src.models.geometry import BoundingBox, normalize_bbox
from .models import LayoutLine

def _runs(mask, horizontal, min_len):
    contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE); out=[]
    for c in contours:
        x,y,w,h=cv2.boundingRect(c)
        length=w if horizontal else h
        thickness=h if horizontal else w
        if length>=min_len and thickness<=max(12,int(length*.08)):
            out.append((x,y,w,h))
    return out

def detect_lines(binary,config):
    h,w=binary.shape[:2]; inv=255-binary if binary.mean()>127 else binary.copy()
    hk=max(15,int(w*float(config.get("horizontal_kernel_ratio",.025))))
    vk=max(15,int(h*float(config.get("vertical_kernel_ratio",.012))))
    hor=cv2.morphologyEx(inv,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,(hk,1)))
    ver=cv2.morphologyEx(inv,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,(1,vk)))
    lines=[]
    for orientation,mask,is_h,min_len in [("H",hor,True,int(w*.015)),("V",ver,False,int(h*.015))]:
        for x,y,lw,lh in _runs(mask,is_h,min_len):
            b=BoundingBox(float(x),float(y),float(x+lw),float(y+lh)); lines.append(LayoutLine(orientation,b,normalize_bbox(b,w,h)))
    return lines,hor,ver
