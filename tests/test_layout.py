import numpy as np, cv2
from src.layout.line_detector import detect_lines
from src.layout.cell_detector import detect_cells

def test_detect_simple_grid():
    img=np.full((600,800),255,np.uint8)
    cv2.rectangle(img,(100,100),(700,400),0,2); cv2.line(img,(400,100),(400,400),0,2); cv2.line(img,(100,250),(700,250),0,2)
    lines,h,v=detect_lines(img,{})
    cells=detect_cells(h,v,800,600,{"min_cell_width_ratio":.01,"min_cell_height_ratio":.01})
    assert any(x.orientation=="H" for x in lines); assert any(x.orientation=="V" for x in lines); assert len(cells)>=4
