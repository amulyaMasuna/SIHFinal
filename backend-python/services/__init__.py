"""Services package for Legal Metrology AI Microservice with lazy module loading."""

def __getattr__(name: str):
    if name == "ImagePreprocessor":
        from .image_preprocessor import ImagePreprocessor
        return ImagePreprocessor
    elif name == "OCREngine":
        from .ocr_engine import OCREngine
        return OCREngine
    elif name == "NLPParser":
        from .nlp_parser import NLPParser
        return NLPParser
    elif name == "LegalMetrologyValidator":
        from .rule_validator import LegalMetrologyValidator
        return LegalMetrologyValidator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "ImagePreprocessor",
    "OCREngine",
    "NLPParser",
    "LegalMetrologyValidator"
]
