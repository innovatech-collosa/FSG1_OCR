from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

from .base import OCREngine
from src.models.geometry import BoundingBox, normalize_bbox
from src.models.ocr import OCRToken


def _plain_result(result: Any) -> dict:
    """Normaliza Result de PaddleX/PaddleOCR 3.x a dict sin acoplar el proyecto a su clase."""
    if isinstance(result, Mapping):
        return dict(result)
    # PaddleOCR 3.x Result expone normalmente .json como propiedad dict-like.
    value = getattr(result, "json", None)
    if callable(value):
        value = value()
    if isinstance(value, Mapping):
        return dict(value)
    # Compatibilidad defensiva con objetos que exponen .res.
    value = getattr(result, "res", None)
    if isinstance(value, Mapping):
        return {"res": dict(value)}
    raise TypeError(f"Resultado PaddleOCR 3.x no reconocido: {type(result)!r}")


def _payload(result: Any) -> dict:
    data = _plain_result(result)
    inner = data.get("res")
    return dict(inner) if isinstance(inner, Mapping) else data


def _bbox_from_geometry(geometry: Any) -> BoundingBox:
    arr = np.asarray(geometry, dtype=float)
    if arr.ndim == 1 and arr.size == 4:
        x0, y0, x1, y1 = arr.tolist()
        return BoundingBox(float(x0), float(y0), float(x1), float(y1))
    if arr.ndim == 2 and arr.shape[1] >= 2:
        return BoundingBox(float(arr[:, 0].min()), float(arr[:, 1].min()),
                           float(arr[:, 0].max()), float(arr[:, 1].max()))
    raise ValueError(f"Geometria OCR invalida: shape={arr.shape}")


class PaddleOCREngine(OCREngine):
    """Adaptador exclusivo para la API de PaddleOCR 3.x.

    El resto de FSG1 solo recibe OCRToken, por lo que no depende de Result, PaddleX,
    rec_polys o rec_boxes.
    """

    def __init__(self, language: str = "es", min_confidence: float = 0.5,
                 device: str | None = None,
                 use_doc_orientation_classify: bool = False,
                 use_doc_unwarping: bool = False,
                 use_textline_orientation: bool = False):
        from paddleocr import PaddleOCR
        self.min_confidence = float(min_confidence)
        kwargs = {
            "lang": language,
            "use_doc_orientation_classify": bool(use_doc_orientation_classify),
            "use_doc_unwarping": bool(use_doc_unwarping),
            "use_textline_orientation": bool(use_textline_orientation),
        }
        if device:
            kwargs["device"] = device
        self.engine = PaddleOCR(**kwargs)

    @classmethod
    def from_config(cls, config: dict) -> "PaddleOCREngine":
        return cls(
            language=config.get("language", "es"),
            min_confidence=config.get("min_confidence", 0.5),
            device=config.get("device"),
            use_doc_orientation_classify=config.get("use_doc_orientation_classify", False),
            use_doc_unwarping=config.get("use_doc_unwarping", False),
            use_textline_orientation=config.get("use_textline_orientation", False),
        )

    def recognize(self, image, page_number: int) -> list[OCRToken]:
        h, w = image.shape[:2]
        tokens: list[OCRToken] = []
        # PaddleOCR 3.x: predict(), no ocr(..., cls=True).
        for result in self.engine.predict(image):
            data = _payload(result)
            texts = list(data.get("rec_texts") or [])
            scores = np.asarray(data.get("rec_scores") if data.get("rec_scores") is not None else [], dtype=float).reshape(-1)
            geometry = data.get("rec_polys")
            if geometry is None:
                geometry = data.get("rec_boxes")
            if geometry is None:
                geometry = data.get("dt_polys")
            if geometry is None:
                if texts:
                    raise ValueError("PaddleOCR devolvio rec_texts sin rec_polys/rec_boxes/dt_polys")
                continue
            geometry = list(geometry)
            if not (len(texts) == len(scores) == len(geometry)):
                raise ValueError(
                    "Resultado PaddleOCR inconsistente: "
                    f"textos={len(texts)}, scores={len(scores)}, cajas={len(geometry)}"
                )
            for text, confidence, shape in zip(texts, scores, geometry):
                text = str(text).strip()
                confidence = float(confidence)
                if not text or confidence < self.min_confidence:
                    continue
                bbox = _bbox_from_geometry(shape)
                tokens.append(OCRToken(text, confidence, page_number, bbox,
                                       normalize_bbox(bbox, w, h)))
        return tokens
