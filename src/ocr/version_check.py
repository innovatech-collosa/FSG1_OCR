from __future__ import annotations
from importlib.metadata import PackageNotFoundError, version

SUPPORTED = {"paddleocr": "3.7.0", "paddlepaddle": "3.2.2"}

def installed_versions():
    result = {}
    for package in SUPPORTED:
        try: result[package] = version(package)
        except PackageNotFoundError: result[package] = None
    return result

def compatibility_report():
    installed = installed_versions()
    return {
        "supported": SUPPORTED,
        "installed": installed,
        "compatible": all(installed[k] == expected for k, expected in SUPPORTED.items()),
    }
