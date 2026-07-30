# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- **A read timeout no longer returns the previous query's answer.** The local
  `TCPSocketTransport` took a query's send and its matching read under separate
  awaits with no lock spanning both, and had no notion of a poisoned stream, so a
  timed-out read left the response stream offset by one and every later query
  returned a stale value with no error anywhere. It is replaced by
  `scpi_core.SCPISocket`, which holds the pair under one transaction and refuses
  a stream it cannot prove is clean (`DesyncError`).

### Changed
- **Transport, connection registry, exceptions and SCPI/path validation now come
  from [`scpi-core`](https://github.com/RFingAdam/scpi-core)**, shared with
  `mcp-rs-cmw500` and `mcp-rs-siggen` instead of maintained as three diverged
  copies. `spectrum_analyzer_mcp.transport` and `.exceptions` are re-export shims,
  so every name importable from them before still is; `TCPSocketTransport` is an
  alias of `SCPISocket`.
- **Every SCPI call site declares its idempotency.** Value assignments are marked
  `SETTING` and may be retried after a transport failure; `*RST`,
  `SYSTem:PRESet`, `INITiate:IMMediate`, `HCOPy:IMMediate`, `CALibration:ALL?`
  and the marker peak searches are marked `ACTION` and never are.
  `CALC:MARK<n>:MAX:NEXT` is the one that matters: each arrival steps to a
  *different* peak.
- **Live connections are held by `scpi_core.ConnectionRegistry`** rather than a
  module-global dict that never expired. Connections idle for 15 minutes are
  evicted, and eviction runs the same disconnect path as `sa_disconnect`.
- `sanitize_scpi_param` now applies its leading-`*` check after stripping leading
  whitespace, so `" *RST"` is rejected. The previous implementation tested the
  raw string and let it through.
- The `visa` extra defers to `scpi-core[visa]` instead of pinning pyvisa itself.

### Added
- **`spectrum-simulator`** — an offline SCPI simulator, which this server
  previously lacked entirely. Serves `sim/nodes/spectrum.yaml` through
  `scpi_core.sim`, with fault injection (`--drop-responses`,
  `--slow-response-ms`, `--close-after`, `--strict-unknown`) so timeout and
  desync handling can be exercised without hardware. Nodes transcribed from
  documentation but unconfirmed on hardware are listed by
  `spectrum-simulator --list-unverified`.
- `RSSpectrumAnalyzerDriver.resync_count`, so repeated stream resyncs — the sign
  that command timeouts are tighter than the sweep times in use — are visible
  rather than dying with the connection.

## [0.3.0] — 2026-05-13

### Changed
- **License: Apache-2.0 → AGPL-3.0-or-later.** Aligns with the
  eng-mcp-suite toolkit-wide AGPL move. The wrapper code goes AGPL;
  R&S hardware and proprietary client software are independent. See
  the
  [LICENSE_SUMMARY](https://github.com/RFingAdam/eng-mcp-suite/blob/main/LICENSE_SUMMARY.md)
  for the toolkit-wide rationale.

## [0.2.0] — 2026-05-13

### Added
- Multi-vendor support beyond R&S — Keysight, Rigol, Siglent SCPI cores.
- Brand assets aligned with eng-mcp-suite design system.
- Prominent "Hardware required" notice in README.

## [0.1.0] - 2025-02-20

### Added
- Initial release
- MCP server for Rohde & Schwarz spectrum/signal analyzers (FSW, FSVA3000, FSV3000, FPL1000)
- SCPI socket transport layer
- Safety validation for all instrument parameters
- 50+ MCP tools for spectrum analyzer control
- Measurement templates: Channel Power, ACLR, EMI Precompliance, Spurious, OBW, Harmonics
- Limit line system with pass/fail checking
- State management for saving/restoring instrument configurations
- Trace data export (CSV)
