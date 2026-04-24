"""llm_encoder pack configuration (RFC-002 §3.2).

Declared dependencies:
    - numpy, hashlib, os, textwrap, logging (stdlib)
    - anthropic (optional)

Declared mutations: none. Producer of `Callable` constraint functions.
Internal cache keyed by proposition string.
"""

DECLARED_DEPENDENCIES = [
    "numpy",
    "anthropic",   # optional — falls back to word-hash when absent
]

DECLARED_MUTATIONS: list = []
