# Architecture

## Internal layout

```
┌──────────────────────────────────────────────────────────────────┐
│  User-facing surfaces                                            │
│  ┌────────────────────┐              ┌────────────────────────┐  │
│  │  MCP server        │              │  Python API:           │  │
│  │  (stdio transport) │              │  import spectrum_analyzer_mcp │
│  └────────────────────┘              └────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────────┐
│  Orchestration: tools/ (62 tools, 14 categories)                │
│  • connection · frequency · amplitude · bandwidth                │
│  • trace · markers · measurements · sweep                        │
│  • export · scpi · templates · limits · state · system           │
└──────────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────────┐
│  Transport abstraction: shared, from scpi-core                  │
│  • scpi_core.SCPISocket      : raw async TCP, desync-aware      │
│  • scpi_core.VISATransport   : PyVISA (GPIB/USB-TMC/HiSLIP)     │
│  • scpi_core.create_transport: auto-detect from params           │
│  • transport/__init__.py     : re-export shim over the above    │
└──────────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────────┐
│  Driver                                                          │
│  • driver/sa_driver.py       : core SCPI driver                 │
│  • driver/scpi_dialect.py    : vendor-specific variations       │
│  • driver/factory.py         : auto-detect vendor from *IDN?    │
└──────────────────────────────────────────────────────────────────┘
                              │
                       SCPI to instrument
```

Concurrent tool calls are serialized per resource: measurement, template and
state each hold their own `asyncio.Lock`, while live analyzer connections are
held by `scpi_core.ConnectionRegistry` (idle TTL plus a single eviction path).
Failed state restores automatically roll back to the previous snapshot.

## Source layout

```
spectrum_analyzer_mcp/
├── server.py              # MCP server entry point
├── config.py              # pydantic-settings
├── tools/                 # 62 tools across 14 modules
│   ├── _registry.py       #   Central routing (handle_tool)
│   ├── _connection.py     #   scpi_core.ConnectionRegistry of live drivers
│   ├── connection.py      #   Connect / disconnect / discover
│   ├── frequency.py
│   ├── amplitude.py
│   ├── bandwidth.py
│   ├── trace.py
│   ├── markers.py
│   ├── measurements.py    #   Channel power, ACLR, OBW, SEM, EVM, CCDF
│   ├── sweep.py
│   ├── export.py          #   CSV / JSON / screenshot
│   ├── scpi.py            #   Raw SCPI access
│   ├── templates_tools.py
│   ├── limits_tools.py
│   ├── state_tools.py
│   └── system.py
├── transport/             # Re-export shim over scpi_core.transport
├── driver/                # SCPI driver + dialect map
├── models/                # TraceData, MarkerData, …
├── templates/             # Built-in measurement templates
├── safety/                # SCPI-injection guard, path validation
├── sim/                   # Offline simulator node map (spectrum-simulator)
├── state.py               # Save / load with rollback
└── limits.py              # Limit-line engine
```

## Position in eng-mcp-suite

`mcp-rs-spectrum-analyzer` sits in the **lab-gear** layer. It talks to
physical analyzers over SCPI.

```
        ┌─────────────────────────────────────┐
        │   AI agent (Claude Code / Desktop)  │
        └──────┬──────────────┬───────────────┘
               │ via MCP      │ via MCP
       ┌───────▼──────────┐ ┌─▼──────────────────────┐
       │ mcp-rs-spectrum  │ │ siblings: vna, siggen, │
       │ -analyzer        │ │ cmw500, emc-regulations│
       └───────┬──────────┘ └────────────────────────┘
               │ trace JSON / CSV
       ┌───────▼──────────────────────┐
       │  downstream consumers:       │
       │  emc-regulations,            │
       │  pcb-emcopilot               │
       └──────────────────────────────┘
```

### Feeds (this MCP produces output that)…

- **mcp-emc-regulations**: measured ACLR / OBW / SEM / harmonics traces feed
  into CISPR / FCC limit cross-references.
- **mcp-pcb-emcopilot**: radiated emissions context for PCB-layout review.

### Consumes (this MCP accepts input from)…

- **mcp-rs-siggen**: coordinated stimulus during EVM / spectrum-flatness
  testing.
- **mcp-emc-regulations**: limit-line definitions for standards-aware
  pass/fail checks.

### Workflow bundles that include this MCP

| Bundle              | Role of this MCP                                  |
| ------------------- | ------------------------------------------------- |
| `lab-automation`    | Spectrum / signal-analyzer measurement leg        |
| `emc-precompliance` | ACLR / OBW / SEM / harmonics against CISPR / FCC  |

---

## Design decisions

- **Transport comes from `scpi-core`, not from here.** `SCPISocket` (raw TCP)
  and `VISATransport` are shared with the sibling R&S servers; the factory
  auto-detects from the resource string. The local `TCPSocketTransport` it
  replaced held a query's send and its matching read under separate awaits, so a
  timed-out read left the stream offset by one and the next query returned the
  previous answer with no error. `SCPISocket` holds the pair under one
  transaction and refuses to use a stream it cannot prove is clean.
- **Every SCPI call site declares its idempotency.** `Idempotency.SETTING` marks
  writes a transport may safely re-send after a failure; `ACTION` marks the ones
  it must not, such as `*RST` and `CALC:MARK1:MAX:NEXT`. That second one steps
  to a *different* peak on every arrival.
- **One asyncio lock per resource class.** Measurement, template and state each
  get their own lock: fine-grained enough to let independent tools run
  concurrently, coarse enough to keep SCPI framing intact. Connections are the
  exception: the shared registry owns their serialization.
- **Offline mode is a node map, not a mock.** `spectrum-simulator` serves
  `sim/nodes/spectrum.yaml` over TCP 5025 through `scpi_core.sim`, so the driver
  is exercised against a command table rather than against `AsyncMock`. Nodes
  marked `verified: false` are the bench checklist:
  `spectrum-simulator --list-unverified`.
- **Safety as defaults, not gates.** SCPI injection and path traversal are
  pre-validated; raw SCPI is on by default but can be turned off with one env
  variable for shared-bench setups.
