from pathlib import Path
import fitz, cv2, numpy as np
from src.models.page import PageInfo, RenderedPage

def render_pdf(pdf_path:Path,dpi:int=300)->list[RenderedPage]:
    doc=fitz.open(pdf_path); pages=[]
    for i,p in enumerate(doc):
        pix=p.get_pixmap(dpi=dpi,alpha=False)
        arr=np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width,pix.n)
        if pix.n==3: arr=cv2.cvtColor(arr,cv2.COLOR_RGB2BGR)
        elif pix.n==4: arr=cv2.cvtColor(arr,cv2.COLOR_RGBA2BGR)
        pages.append(RenderedPage(PageInfo(i+1,pix.width,pix.height,dpi),arr.copy()))
    doc.close(); return pages
