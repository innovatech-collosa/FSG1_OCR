import cv2

def draw_ocr_overlay(image,tokens):
    out=image.copy()
    for t in tokens:
        b=t.bbox_px; p1=(int(b.x0),int(b.y0)); p2=(int(b.x1),int(b.y1))
        cv2.rectangle(out,p1,p2,(0,190,0),2)
        cv2.putText(out,f"{t.text} {t.confidence:.2f}",(p1[0],max(15,p1[1]-5)),cv2.FONT_HERSHEY_SIMPLEX,.4,(0,80,220),1,cv2.LINE_AA)
    return out
