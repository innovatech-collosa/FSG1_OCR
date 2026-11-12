from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class BoundingBox:
    x0: float; y0: float; x1: float; y1: float
    @property
    def width(self): return self.x1-self.x0
    @property
    def height(self): return self.y1-self.y0
    @property
    def center_x(self): return (self.x0+self.x1)/2
    @property
    def center_y(self): return (self.y0+self.y1)/2
    def to_dict(self): return asdict(self)

def normalize_bbox(b: BoundingBox, width: int, height: int) -> BoundingBox:
    return BoundingBox(b.x0/width,b.y0/height,b.x1/width,b.y1/height)
