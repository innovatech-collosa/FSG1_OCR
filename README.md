# FSG1_OCR V2.1.0

Base limpia del nuevo pipeline. V2.1.0 solo realiza: PDF -> renderizado visual -> preprocesado conservador -> OCR neutro -> diagnostico.

No interpreta campos FSG1, casillas, matrices SI/NO/NA ni respuestas.

## Instalacion
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Uso
Procesar todos los PDF de `input/`:
```bash
python main.py
```
Procesar un PDF:
```bash
python main.py /ruta/documento.pdf
```
Procesar una carpeta:
```bash
python main.py /ruta/carpeta
```

Cada documento genera `pages/`, `diagnostic/`, `ocr.json` y `report.json` en `output/<nombre>/`.

## Compatibilidad comprobada

Esta version usa exclusivamente la API 3.x: `PaddleOCR(...).predict(image)`.
Objetivo verificado: PaddleOCR 3.7.0 y PaddlePaddle 3.2.2.

```bash
python check_environment.py
```

Los avisos de `requests` o ausencia de `ccache` no detienen el OCR. `ccache` solo afecta a posibles recompilaciones.

## V2.1.0 Layout
Genera además `layout.json` y `diagnostic/page_XXX_layout_overlay.png`. Detecta líneas horizontales/verticales, candidatos a celda, asigna tokens por centro geométrico y crea relaciones `NEAREST_RIGHT`/`NEAREST_BELOW`. No interpreta todavía campos FSG1 ni marcas.
