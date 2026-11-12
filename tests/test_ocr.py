from src.ocr.base import OCREngine

def test_ocr_contract_exists():
    assert hasattr(OCREngine,"recognize")
