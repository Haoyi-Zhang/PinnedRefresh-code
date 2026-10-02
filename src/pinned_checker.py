"""Pin-aware certificate checker. Does not import any producer or eliminator."""
from .pinned import to_trace
from .checker import _verify_validated

def verify_pinned(case: dict, certificate: dict) -> bool:
    return _verify_validated(to_trace(case), certificate)
