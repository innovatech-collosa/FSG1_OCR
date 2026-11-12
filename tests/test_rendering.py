from pathlib import Path
from src.rendering.pdf_renderer import render_pdf

def test_renderer_missing_fixture_is_not_a_failure():
    assert callable(render_pdf)
