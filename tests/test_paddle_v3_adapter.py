import numpy as np
from src.ocr.paddle_engine import PaddleOCREngine, _bbox_from_geometry, _payload

class FakeResult:
    def __init__(self, data): self.json = {"res": data}

class FakePipeline:
    def __init__(self, results): self.results = results
    def predict(self, image): return self.results

def engine_with(results, threshold=.5):
    obj=PaddleOCREngine.__new__(PaddleOCREngine)
    obj.min_confidence=threshold
    obj.engine=FakePipeline(results)
    return obj

def test_paddleocr_3_result_rec_polys():
    data={"rec_texts":["MUTUA",""],"rec_scores":np.array([.99,.98]),
          "rec_polys":np.array([[[10,20],[50,20],[50,40],[10,40]],[[1,1],[2,1],[2,2],[1,2]]])}
    tokens=engine_with([FakeResult(data)]).recognize(np.zeros((100,200,3),dtype=np.uint8),1)
    assert len(tokens)==1 and tokens[0].text=="MUTUA"
    assert tokens[0].bbox_norm.x0==.05 and tokens[0].bbox_norm.y0==.2

def test_fallback_rec_boxes_and_threshold():
    data={"rec_texts":["A","B"],"rec_scores":[.49,.75],"rec_boxes":[[0,0,10,10],[20,30,50,60]]}
    tokens=engine_with([{"res":data}],.5).recognize(np.zeros((100,100,3),dtype=np.uint8),2)
    assert [t.text for t in tokens]==["B"] and tokens[0].page==2

def test_mismatch_raises():
    data={"rec_texts":["A"],"rec_scores":[],"rec_boxes":[[0,0,1,1]]}
    try: engine_with([{"res":data}]).recognize(np.zeros((10,10,3),dtype=np.uint8),1)
    except ValueError as e: assert "inconsistente" in str(e)
    else: raise AssertionError("Debio fallar")

def test_polygon_and_box_geometry():
    assert _bbox_from_geometry([[2,3],[8,4],[7,9],[1,8]]).to_dict()=={"x0":1.0,"y0":3.0,"x1":8.0,"y1":9.0}
    assert _bbox_from_geometry([2,3,8,9]).to_dict()=={"x0":2.0,"y0":3.0,"x1":8.0,"y1":9.0}
