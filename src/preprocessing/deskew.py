import cv2, numpy as np

def deskew(image:np.ndarray,max_degrees:float=5.0)->np.ndarray:
    gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    _,bw=cv2.threshold(gray,0,255,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
    pts=np.column_stack(np.where(bw>0))
    if len(pts)<100: return image.copy()
    angle=cv2.minAreaRect(pts[:,::-1].astype(np.float32))[-1]
    angle=angle-90 if angle>45 else angle
    if abs(angle)>max_degrees or abs(angle)<0.05: return image.copy()
    h,w=image.shape[:2]; m=cv2.getRotationMatrix2D((w/2,h/2),angle,1)
    return cv2.warpAffine(image,m,(w,h),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_REPLICATE)
