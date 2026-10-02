"""Producer wrapper: pin equations are zero constraints, not leaked deltas."""
from .pinned import to_trace
from .producer import _produce_validated

def produce_pinned(case: dict) -> dict:
    return _produce_validated(to_trace(case))
