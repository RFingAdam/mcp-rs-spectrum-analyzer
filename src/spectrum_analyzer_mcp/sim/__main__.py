"""``spectrum-simulator`` console script.

A thin wrapper over ``scpi-sim`` with this repo's node map preselected. Every
flag the shared CLI offers -- including the fault injection that exists so a
client's timeout and desync handling can be exercised deliberately
(``--drop-responses``, ``--extra-responses``, ``--close-after``,
``--slow-response-ms``, ``--strict-unknown``, ``--time-scale``) -- is available
here unchanged, because reimplementing a subset is how the two drift apart.
"""

import sys

from scpi_core.sim.__main__ import main as sim_main

from . import NODE_MAP


def main(argv: list[str] | None = None) -> int:
    return sim_main(
        argv,
        prog="spectrum-simulator",
        default_nodes=str(NODE_MAP),
    )


if __name__ == "__main__":
    sys.exit(main())
