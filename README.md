# R&S Spectrum Analyzer MCP Server

MCP server for Rohde & Schwarz spectrum/signal analyzer automation via TCP/IP SCPI.

## Supported Instruments

- **FSW** - High-end signal and spectrum analyzer (up to 90 GHz)
- **FSVA3000** - Mid-range high performance signal and spectrum analyzer
- **FSV3000** - Mid-range workhorse signal and spectrum analyzer
- **FPL1000** - Entry-level spectrum analyzer (up to 40 GHz)

## Installation

```bash
uv pip install -e ".[dev]"
```

## Configuration

Copy `.env.example` to `.env` and configure for your instrument:

```bash
cp .env.example .env
# Edit .env with your instrument's IP address
```

## Usage

### With Claude Desktop

Add to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "spectrum-analyzer": {
      "command": "rs-spectrum-analyzer-mcp"
    }
  }
}
```

### Direct execution

```bash
rs-spectrum-analyzer-mcp
```

## Available Tools

### Connection
- `sa_discover` - Scan for spectrum analyzers on the network
- `sa_connect` - Connect to a spectrum analyzer
- `sa_disconnect` - Disconnect from a spectrum analyzer
- `sa_identify` - Get instrument identification
- `sa_get_status` - Get instrument status

### Frequency Control
- `sa_set_center_span` - Set center frequency and span
- `sa_set_start_stop` - Set start/stop frequencies
- `sa_set_frequency_step` - Set frequency step size
- `sa_full_span` - Set full span

### Amplitude Control
- `sa_set_reference_level` - Set reference level
- `sa_set_attenuation` - Set input attenuation
- `sa_set_preamp` - Enable/disable preamplifier
- `sa_set_scale` - Set Y-axis scale (dB/div)

### Bandwidth Control
- `sa_set_rbw` - Set resolution bandwidth
- `sa_set_vbw` - Set video bandwidth
- `sa_set_sweep_time` - Set sweep time
- `sa_auto_coupling` - Set auto-coupled bandwidths

### Trace Operations
- `sa_get_trace_data` - Read trace data
- `sa_set_trace_mode` - Set trace mode (write/maxhold/minhold/average)
- `sa_set_averaging_count` - Set average count
- `sa_clear_trace` - Clear/reset trace
- `sa_set_detector` - Set detector type

### Markers
- `sa_set_marker` - Position a marker
- `sa_get_marker` - Read marker value
- `sa_peak_search` - Find peak on trace
- `sa_next_peak` - Find next peak
- `sa_marker_to_center` - Set center freq to marker
- `sa_marker_delta` - Enable delta marker
- `sa_marker_bandwidth` - N-dB bandwidth measurement

### Measurements
- `sa_measure_channel_power` - Channel power measurement
- `sa_measure_aclr` - Adjacent channel leakage ratio
- `sa_measure_obw` - Occupied bandwidth
- `sa_measure_sem` - Spectrum emission mask
- `sa_measure_evm` - Error vector magnitude
- `sa_measure_ccdf` - Complementary cumulative distribution function

### Sweep Control
- `sa_single_sweep` - Trigger single sweep
- `sa_continuous_sweep` - Enable continuous sweep
- `sa_set_trigger` - Configure trigger

### Export
- `sa_save_trace_csv` - Save trace data to CSV
- `sa_save_screenshot` - Save screenshot
- `sa_export_trace_data` - Export trace data as JSON

### Raw SCPI
- `sa_scpi_send` - Send raw SCPI command
- `sa_scpi_query` - Send raw SCPI query
- `sa_reset` - Reset instrument (*RST)
- `sa_preset` - Preset instrument

### Templates
- `sa_list_templates` - List available templates
- `sa_load_template` - Load a measurement template
- `sa_apply_template` - Apply template to instrument

### Limits
- `sa_define_limit` - Define a limit line
- `sa_check_limits` - Check trace against limits
- `sa_clear_limits` - Clear all limits
- `sa_list_limits` - List defined limits

### State Management
- `sa_save_state` - Save instrument state
- `sa_load_state` - Load instrument state
- `sa_get_full_state` - Get complete instrument state

## Development

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Run tests
uv run pytest tests/ -v

# Lint
uv run ruff check src/ tests/
```

## License

Apache-2.0
