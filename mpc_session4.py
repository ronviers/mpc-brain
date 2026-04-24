"""Top-level alias for `experiments.historical.mpc_session4`.

See mpc_session2.py for the rationale. Same pattern.
"""

import sys as _sys

from experiments.historical import mpc_session4 as _real

_sys.modules[__name__] = _real
