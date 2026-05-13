# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
