from dataclasses import dataclass
import numpy as np

@dataclass
class PageInfo:
    number:int; width:int; height:int; dpi:int

@dataclass
class RenderedPage:
    info:PageInfo; image:np.ndarray

@dataclass
class PageImages:
    original:np.ndarray; ocr:np.ndarray; binary:np.ndarray
