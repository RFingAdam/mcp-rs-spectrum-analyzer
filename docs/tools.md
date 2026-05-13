# Tools

This page documents the 62 MCP tools the server exposes. Tools are registered
under the `spectrum-analyzer` namespace when the server is loaded by an MCP
client.

## Tool index

### Connection (5)

| Tool | Purpose |
| ---- | ------- |
| `sa_discover` | Scan for spectrum analyzers on the network |
| `sa_connect` | Connect to a spectrum analyzer (TCP or VISA) |
| `sa_disconnect` | Disconnect from a spectrum analyzer |
| `sa_identify` | Get instrument identification (`*IDN?`) |
| `sa_get_status` | Get connection and configuration status |

### Frequency (4)

| Tool | Purpose |
| ---- | ------- |
| `sa_set_center_span` | Set center frequency and span |
| `sa_set_start_stop` | Set start/stop frequencies |
| `sa_set_frequency_step` | Set frequency step size |
| `sa_full_span` | Set full span |

### Amplitude (4)

| Tool | Purpose |
| ---- | ------- |
| `sa_set_reference_level` | Set reference level |
| `sa_set_attenuation` | Set input attenuation |
| `sa_set_preamp` | Enable/disable preamplifier |
| `sa_set_scale` | Set Y-axis scale (dB/div) |

### Bandwidth (4)

| Tool | Purpose |
| ---- | ------- |
| `sa_set_rbw` | Set resolution bandwidth |
| `sa_set_vbw` | Set video bandwidth |
| `sa_set_sweep_time` | Set sweep time |
| `sa_auto_coupling` | Set auto-coupled bandwidths |

### Trace (5)

| Tool | Purpose |
| ---- | ------- |
| `sa_get_trace_data` | Read trace data (frequencies + amplitudes) |
| `sa_set_trace_mode` | Set trace mode (write / maxhold / minhold / average) |
| `sa_set_averaging_count` | Set average count |
| `sa_clear_trace` | Clear/reset trace |
| `sa_set_detector` | Set detector type (peak / RMS / quasi-peak / sample) |

### Markers (7)

| Tool | Purpose |
| ---- | ------- |
| `sa_set_marker` | Position a marker at a frequency |
| `sa_get_marker` | Read marker value |
| `sa_peak_search` | Find peak on trace |
| `sa_next_peak` | Find next peak |
| `sa_marker_to_center` | Set center frequency to marker position |
| `sa_marker_delta` | Enable delta marker mode |
| `sa_marker_bandwidth` | N-dB bandwidth measurement |

### Measurements (6)

| Tool | Purpose |
| ---- | ------- |
| `sa_measure_channel_power` | Channel power measurement |
| `sa_measure_aclr` | Adjacent channel leakage ratio |
| `sa_measure_obw` | Occupied bandwidth |
| `sa_measure_sem` | Spectrum emission mask |
| `sa_measure_evm` | Error vector magnitude |
| `sa_measure_ccdf` | Complementary cumulative distribution function |

### Sweep (3)

| Tool | Purpose |
| ---- | ------- |
| `sa_single_sweep` | Trigger single sweep and wait |
| `sa_continuous_sweep` | Enable continuous sweep |
| `sa_set_trigger` | Configure trigger source and level |

### Export (4)

| Tool | Purpose |
| ---- | ------- |
| `sa_save_trace_csv` | Save trace data to CSV |
| `sa_save_trace_json` | Save trace data to JSON with instrument metadata |
| `sa_save_screenshot` | Save screenshot on instrument |
| `sa_export_trace_data` | Export trace data as JSON response |

### Raw SCPI (4)

| Tool | Purpose |
| ---- | ------- |
| `sa_scpi_send` | Send raw SCPI command (with injection protection) |
| `sa_scpi_query` | Send raw SCPI query |
| `sa_reset` | Reset instrument (`*RST`) |
| `sa_preset` | Preset instrument |

### Templates (3)

| Tool | Purpose |
| ---- | ------- |
| `sa_list_templates` | List available measurement templates |
| `sa_load_template` | Load a measurement template |
| `sa_apply_template` | Apply loaded template to instrument |

Built-in templates: `channel_power`, `aclr`, `obw`, `emi` (CISPR 32 Class B),
`harmonics`, `spurious`.

### Limits (4)

| Tool | Purpose |
| ---- | ------- |
| `sa_define_limit` | Define a limit line with segments |
| `sa_check_limits` | Check trace data against defined limits |
| `sa_clear_limits` | Clear all limit definitions |
| `sa_list_limits` | List all defined limits |

### State (3)

| Tool | Purpose |
| ---- | ------- |
| `sa_save_state` | Save instrument state (with rollback on failure) |
| `sa_load_state` | Restore instrument state |
| `sa_get_full_state` | Get complete instrument configuration |

### System (6)

| Tool | Purpose |
| ---- | ------- |
| `sa_get_error_queue` | Read all errors from instrument error queue |
| `sa_set_display_update` | Enable/disable display updates |
| `sa_run_alignment` | Run internal self-alignment/calibration |
| `sa_set_sweep_points` | Set number of sweep trace points |
| `sa_get_sweep_points` | Get current number of sweep points |
| `sa_capture_screenshot` | Capture screenshot as base64 PNG |

---

## Source of truth

Tool definitions live in
[`src/spectrum_analyzer_mcp/tools/`](../src/spectrum_analyzer_mcp/tools/),
one module per category. Each tool has a complete JSON-Schema `inputSchema`
declared at registration — arguments, defaults, and units are documented
inline there.
