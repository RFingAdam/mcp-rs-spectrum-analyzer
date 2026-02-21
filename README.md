# Spectrum Analyzer MCP Server

[![CI](https://github.com/RFingAdam/mcp-rs-spectrum-analyzer/actions/workflows/ci.yml/badge.svg)](https://github.com/RFingAdam/mcp-rs-spectrum-analyzer/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-green.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-compatible-purple.svg)](https://modelcontextprotocol.io)

[Model Context Protocol](https://modelcontextprotocol.io) server for automating spectrum and signal analyzers via SCPI. Connect any MCP-compatible AI assistant (Claude Desktop, Claude Code, etc.) to your test equipment for hands-free RF measurements, EMC pre-compliance testing, and automated test sequences.

## Supported Instruments

| Vendor | Families | Transport | Status |
|--------|----------|-----------|--------|
| **Rohde & Schwarz** | FSW, FSVA3000, FSV3000, FPL1000 | TCP, VISA | Full support |
| **Keysight** | N90x0, UXA, PXA, MXA, EXA, CXA | TCP, VISA | SCPI core |
| **Rigol** | DSA800, RSA5000, RSA3000 | TCP, VISA | SCPI core |
| **Siglent** | SSA3000X, SVA1000X | TCP, VISA | SCPI core |
| **Anritsu** | MS2760, MS2090 | TCP, VISA | SCPI core |
| **Tektronix** | RSA500, RSA600 | TCP, VISA | SCPI core |

> **Full support** = vendor-specific result parsing and family detection. **SCPI core** = standard SCPI commands (frequency, amplitude, markers, trace, sweep). All vendors share 95%+ identical SCPI command sets.

## Quick Start

### Install

```bash
uv pip install -e .

# Optional: VISA support for GPIB/USB/HiSLIP
uv pip install -e ".[visa]"
```

### Configure

Set your instrument's IP via environment variable or `.env` file:

```bash
export SA_HOST=192.168.1.100
export SA_PORT=5025  # Default for R&S, Keysight, Siglent
```

<details>
<summary>All configuration options</summary>

| Variable | Default | Description |
|----------|---------|-------------|
| `SA_HOST` | `192.168.1.100` | Instrument IP address |
| `SA_PORT` | `5025` | SCPI port (5025 for R&S/Keysight/Siglent, 5555 for Rigol) |
| `SA_TIMEOUT` | `5.0` | Connection timeout (seconds) |
| `SA_COMMAND_TIMEOUT` | `10.0` | SCPI command timeout (seconds) |
| `SA_DISCOVERY_TIMEOUT` | `2.0` | Network discovery timeout (seconds) |
| `SA_RESOURCE_STRING` | `None` | VISA resource string (overrides host/port) |
| `SA_SAFE_DIRECTORIES` | `["."]` | Allowed directories for file export |
| `SA_MAX_EXPORT_SIZE_MB` | `100` | Maximum export file size (MB) |
| `SA_RAW_SCPI_ENABLED` | `true` | Enable/disable raw SCPI commands |

</details>

### Use with Claude Desktop

Add to your Claude Desktop MCP configuration (`~/.claude/mcp.json`):

```json
{
  "mcpServers": {
    "spectrum-analyzer": {
      "command": "spectrum-analyzer-mcp"
    }
  }
}
```

### Use with Claude Code

Add to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "spectrum-analyzer": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/mcp-rs-spectrum-analyzer", "spectrum-analyzer-mcp"]
    }
  }
}
```

### VISA Connections

For instruments connected via GPIB, USB-TMC, or HiSLIP (requires `pyvisa`):

```bash
# GPIB
sa_connect --resource "GPIB::1::INSTR"

# USB-TMC
sa_connect --resource "USB::0x0AAD::0x0119::100001::INSTR"

# HiSLIP
sa_connect --resource "TCPIP::192.168.1.100::hislip0::INSTR"
```

## Available Tools (62)

### Connection (5)
| Tool | Description |
|------|-------------|
| `sa_discover` | Scan for spectrum analyzers on the network |
| `sa_connect` | Connect to a spectrum analyzer (TCP or VISA) |
| `sa_disconnect` | Disconnect from a spectrum analyzer |
| `sa_identify` | Get instrument identification (*IDN?) |
| `sa_get_status` | Get connection and configuration status |

### Frequency Control (4)
| Tool | Description |
|------|-------------|
| `sa_set_center_span` | Set center frequency and span |
| `sa_set_start_stop` | Set start/stop frequencies |
| `sa_set_frequency_step` | Set frequency step size |
| `sa_full_span` | Set full span |

### Amplitude Control (4)
| Tool | Description |
|------|-------------|
| `sa_set_reference_level` | Set reference level |
| `sa_set_attenuation` | Set input attenuation |
| `sa_set_preamp` | Enable/disable preamplifier |
| `sa_set_scale` | Set Y-axis scale (dB/div) |

### Bandwidth Control (4)
| Tool | Description |
|------|-------------|
| `sa_set_rbw` | Set resolution bandwidth |
| `sa_set_vbw` | Set video bandwidth |
| `sa_set_sweep_time` | Set sweep time |
| `sa_auto_coupling` | Set auto-coupled bandwidths |

### Trace Operations (5)
| Tool | Description |
|------|-------------|
| `sa_get_trace_data` | Read trace data (frequencies + amplitudes) |
| `sa_set_trace_mode` | Set trace mode (write/maxhold/minhold/average) |
| `sa_set_averaging_count` | Set average count |
| `sa_clear_trace` | Clear/reset trace |
| `sa_set_detector` | Set detector type (peak/RMS/quasi-peak/sample) |

### Markers (7)
| Tool | Description |
|------|-------------|
| `sa_set_marker` | Position a marker at a frequency |
| `sa_get_marker` | Read marker value |
| `sa_peak_search` | Find peak on trace |
| `sa_next_peak` | Find next peak |
| `sa_marker_to_center` | Set center frequency to marker position |
| `sa_marker_delta` | Enable delta marker mode |
| `sa_marker_bandwidth` | N-dB bandwidth measurement |

### Measurements (6)
| Tool | Description |
|------|-------------|
| `sa_measure_channel_power` | Channel power measurement |
| `sa_measure_aclr` | Adjacent channel leakage ratio |
| `sa_measure_obw` | Occupied bandwidth |
| `sa_measure_sem` | Spectrum emission mask |
| `sa_measure_evm` | Error vector magnitude |
| `sa_measure_ccdf` | Complementary cumulative distribution function |

### Sweep Control (3)
| Tool | Description |
|------|-------------|
| `sa_single_sweep` | Trigger single sweep and wait |
| `sa_continuous_sweep` | Enable continuous sweep |
| `sa_set_trigger` | Configure trigger source and level |

### Export (4)
| Tool | Description |
|------|-------------|
| `sa_save_trace_csv` | Save trace data to CSV file |
| `sa_save_trace_json` | Save trace data to JSON with instrument metadata |
| `sa_save_screenshot` | Save screenshot on instrument |
| `sa_export_trace_data` | Export trace data as JSON response |

### Raw SCPI (4)
| Tool | Description |
|------|-------------|
| `sa_scpi_send` | Send raw SCPI command (with injection protection) |
| `sa_scpi_query` | Send raw SCPI query |
| `sa_reset` | Reset instrument (*RST) |
| `sa_preset` | Preset instrument |

### Templates (3)
| Tool | Description |
|------|-------------|
| `sa_list_templates` | List available measurement templates |
| `sa_load_template` | Load a measurement template |
| `sa_apply_template` | Apply loaded template to instrument |

Built-in templates: `channel_power`, `aclr`, `obw`, `emi` (CISPR 32 Class B), `harmonics`, `spurious`.

### Limits (4)
| Tool | Description |
|------|-------------|
| `sa_define_limit` | Define a limit line with segments |
| `sa_check_limits` | Check trace data against defined limits |
| `sa_clear_limits` | Clear all limit definitions |
| `sa_list_limits` | List all defined limits |

### State Management (3)
| Tool | Description |
|------|-------------|
| `sa_save_state` | Save instrument state (with rollback on failure) |
| `sa_load_state` | Restore instrument state |
| `sa_get_full_state` | Get complete instrument configuration |

### System (6)
| Tool | Description |
|------|-------------|
| `sa_get_error_queue` | Read all errors from instrument error queue |
| `sa_set_display_update` | Enable/disable display updates |
| `sa_run_alignment` | Run internal self-alignment/calibration |
| `sa_set_sweep_points` | Set number of sweep trace points |
| `sa_get_sweep_points` | Get current number of sweep points |
| `sa_capture_screenshot` | Capture screenshot as base64 PNG |

## Architecture

```
spectrum_analyzer_mcp/
  server.py              # MCP server entry point
  config.py              # Pydantic settings (env vars)
  tools/                 # 62 tools across 14 modules
    __init__.py          #   Aggregates all tools + handlers
    _registry.py         #   Central routing (handle_tool)
    _connection.py       #   Connection pool + locks
    connection.py        #   Connect/disconnect/discover
    frequency.py         #   Frequency control
    amplitude.py         #   Amplitude control
    bandwidth.py         #   RBW/VBW/sweep time
    trace.py             #   Trace read/configure
    markers.py           #   Marker operations
    measurements.py      #   Channel power, ACLR, OBW, SEM, EVM, CCDF
    sweep.py             #   Sweep control + trigger
    export.py            #   CSV/JSON/screenshot export
    scpi.py              #   Raw SCPI access
    templates_tools.py   #   Measurement templates
    limits_tools.py      #   Limit lines
    state_tools.py       #   Save/load instrument state
    system.py            #   Error queue, display, alignment
  transport/             # Transport abstraction layer
    base.py              #   SCPITransport ABC
    tcp_socket.py        #   TCP/IP socket transport
    visa.py              #   PyVISA transport (GPIB/USB/HiSLIP)
    factory.py           #   Auto-detect transport from params
  driver/                # Instrument driver
    sa_driver.py         #   Core SCPI driver
    scpi_dialect.py      #   Vendor-specific SCPI variations
    factory.py           #   Auto-detect vendor from *IDN?
  models/                # Data models (TraceData, MarkerData, etc.)
  templates/             # Built-in measurement templates
  safety/                # SCPI injection protection, path validation
  state.py               # State save/load with rollback
  limits.py              # Limit line engine
```

## Security

- **SCPI injection protection** -- All user-supplied parameters are sanitized before inclusion in SCPI commands
- **Path traversal protection** -- File export paths are validated against configured safe directories
- **Raw SCPI guard** -- `sa_scpi_send`/`sa_scpi_query` can be disabled via `SA_RAW_SCPI_ENABLED=false`
- **Asyncio locks** -- Concurrent tool calls are serialized per resource (connection, measurement, template)
- **State rollback** -- Failed state restore operations automatically roll back to previous state

## Development

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Run tests (250 tests)
uv run pytest tests/ -v

# Lint + format
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/

# Type check
uv run mypy src/
```

## License

Apache-2.0
