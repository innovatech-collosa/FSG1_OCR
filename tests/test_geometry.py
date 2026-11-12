from src.models.geometry import BoundingBox, normalize_bbox

def test_normalize_bbox():
    b=normalize_bbox(BoundingBox(100,200,300,600),1000,2000)
    assert b==BoundingBox(.1,.1,.3,.3)
