from dataclasses import dataclass
from .geometry import BoundingBox

@dataclass
class OCRToken:
    text:str; confidence:float; page:int; bbox_px:BoundingBox; bbox_norm:BoundingBox
    def to_dict(self):
        return {"text":self.text,"confidence":round(float(self.confidence),6),"bbox_px":self.bbox_px.to_dict(),"bbox_norm":self.bbox_norm.to_dict()}

@dataclass
class OCRLine:
    text:str; tokens:list[OCRToken]; bbox_px:BoundingBox; bbox_norm:BoundingBox
    def to_dict(self):
        return {"text":self.text,"token_count":len(self.tokens),"bbox_px":self.bbox_px.to_dict(),"bbox_norm":self.bbox_norm.to_dict()}
