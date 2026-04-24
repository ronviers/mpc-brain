"""llm_encoder pack — natural-language → constraint-function encoder.

Canonical home of `LLMConstraintEncoder`, previously defined inside
`experiments/historical/mpc_session2.py`. The historical module now
re-exports from this pack.
"""

from .pack import LLMConstraintEncoder

__all__ = ["LLMConstraintEncoder"]
