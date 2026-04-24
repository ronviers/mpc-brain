"""Top-level alias for `experiments.historical.mpc_session2`.

The canonical copy of the Session-2 monolith lives under
`experiments/historical/` per RFC-002 §13.2(b). Session-5-era code
imports it by bare module name (`from mpc_session2 import ...`); this
shim re-aliases the historical module into the top-level namespace so
those call sites resolve without duplicating code or classes.

The aliasing via `sys.modules[__name__] = _real` ensures that
`import mpc_session2` and `import experiments.historical.mpc_session2`
yield the *same* module object — so classes are not duplicated and
`isinstance` checks stay consistent across import paths.
"""

import sys as _sys

from experiments.historical import mpc_session2 as _real

_sys.modules[__name__] = _real
