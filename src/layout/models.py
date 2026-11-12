from dataclasses import dataclass, asdict
from src.models.geometry import BoundingBox

@dataclass
class LayoutLine:
    orientation:str; bbox_px:BoundingBox; bbox_norm:BoundingBox
    def to_dict(self): return {"orientation":self.orientation,"bbox_px":self.bbox_px.to_dict(),"bbox_norm":self.bbox_norm.to_dict()}

@dataclass
class Cell:
    id:str; bbox_px:BoundingBox; bbox_norm:BoundingBox; token_indexes:list[int]
    def to_dict(self): return {"id":self.id,"bbox_px":self.bbox_px.to_dict(),"bbox_norm":self.bbox_norm.to_dict(),"token_indexes":self.token_indexes}

@dataclass
class SpatialRelation:
    source:str; target:str; relation:str; distance:float
    def to_dict(self): return asdict(self)
