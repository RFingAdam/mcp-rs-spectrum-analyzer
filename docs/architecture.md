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
│  Orchestration — tools/ (62 tools, 14 categories)                │
│  • connection · frequency · amplitude · bandwidth                │
│  • trace · markers · measurements · sweep                        │
│  • export · scpi · templates · limits · state · system           │
└──────────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────────┐
│  Transport abstraction                                           │
│  • transport/tcp_socket.py    — raw async TCP                    │
│  • transport/visa.py          — PyVISA (GPIB/USB-TMC/HiSLIP)     │
│  • transport/factory.py       — auto-detect from params          │
└──────────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────────┐
│  Driver                                                          │
│  • driver/sa_driver.py        — core SCPI driver                 │
│  • driver/scpi_dialect.py     — vendor-specific variations       │
│  • driver/factory.py          — auto-detect vendor from *IDN?    │
└──────────────────────────────────────────────────────────────────┘
                              │
                       SCPI to instrument
```

Concurrent tool calls are serialized per resource (connection, measurement,
template) with `asyncio.Lock`. Failed state restores automatically roll back
to the previous snapshot.

## Source layout

```
spectrum_analyzer_mcp/
├── server.py              # MCP server entry point
├── config.py              # pydantic-settings
├── tools/                 # 62 tools across 14 modules
│   ├── _registry.py       #   Central routing (handle_tool)
│   ├── _connection.py     #   Connection pool + locks
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
├── transport/             # TCP / VISA / factory
├── driver/                # SCPI driver + dialect map
├── models/                # TraceData, MarkerData, …
├── templates/             # Built-in measurement templates
├── safety/                # SCPI-injection guard, path validation
├── state.py               # Save / load with rollback
└── limits.py              # Limit-line engine
```

## Position in eng-mcp-suite

`mcp-rs-spectrum-analyzer` sits in the **lab-gear** layer — it talks to
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

- **mcp-emc-regulations** — measured ACLR / OBW / SEM / harmonics traces feed
  into CISPR / FCC limit cross-references.
- **mcp-pcb-emcopilot** — radiated emissions context for PCB-layout review.

### Consumes (this MCP accepts input from)…

- **mcp-rs-siggen** — coordinated stimulus during EVM / spectrum-flatness
  testing.
- **mcp-emc-regulations** — limit-line definitions for standards-aware
  pass/fail checks.

### Workflow bundles that include this MCP

| Bundle              | Role of this MCP                                  |
| ------------------- | ------------------------------------------------- |
| `lab-automation`    | Spectrum / signal-analyzer measurement leg        |
| `emc-precompliance` | ACLR / OBW / SEM / harmonics against CISPR / FCC  |

---

## Design decisions

- **Transport-agnostic.** Same driver, two transports (`tcp_socket` and
  `pyvisa`). The factory auto-detects from the resource string.
- **One asyncio lock per resource class.** Connection, measurement, template,
  and state each get their own lock — fine-grained enough to let independent
  tools run concurrently, coarse enough to keep SCPI framing intact.
- **Safety as defaults, not gates.** SCPI injection and path traversal are
  pre-validated; raw SCPI is on by default but can be turned off with one env
  variable for shared-bench setups.
