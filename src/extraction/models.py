from dataclasses import dataclass
from typing import Any

@dataclass
class Token:
    text: str
    confidence: float
    page: int
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def cx(self): return (self.x0+self.x1)/2
    @property
    def cy(self): return (self.y0+self.y1)/2
    @property
    def height(self): return self.y1-self.y0

@dataclass
class ExtractedValue:
    value: Any
    status: str
    source: str | None = None
