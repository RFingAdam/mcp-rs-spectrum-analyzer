# Usage

A practical end-to-end walkthrough. For the full tool reference, see [Tools](tools.md).

---

## Scenario: 5 GHz Wi-Fi pre-compliance ACLR sweep against CISPR 32

You have a 5 GHz Wi-Fi DUT on the bench, transmitting at 5.2 GHz. You want to
run an ACLR measurement, capture the trace, and compare against the
CISPR 32 Class B limit line.

## Setup

```bash
uv pip install -e .
```

Register the MCP server with Claude Desktop:

```json
{
  "mcpServers": {
    "spectrum-analyzer": {
      "command": "spectrum-analyzer-mcp"
    }
  }
}
```

Set environment for the SA:

```bash
export SA_HOST=192.168.1.100
export SA_PORT=5025
```

Restart your MCP client.

## Step 1 — connect

> *"Connect to the SA and tell me what it is."*

The agent calls `sa_connect`, then `sa_identify`:

```json
{
  "manufacturer": "Rohde&Schwarz",
  "model": "FSW43",
  "serial": "100123",
  "firmware": "3.50"
}
```

## Step 2 — configure the measurement

> *"Center 5.2 GHz, span 100 MHz, RBW 100 kHz, ref level 0 dBm. Use the CISPR 32 Class B EMI template."*

The agent runs:

```
sa_set_center_span(center_hz=5.2e9, span_hz=100e6)
sa_set_rbw(rbw_hz=100e3)
sa_set_reference_level(level_dbm=0)
sa_load_template(name="emi")
sa_apply_template()
```

The EMI template flips the detector to quasi-peak and pulls in the
CISPR 32 Class B limit line.

## Step 3 — single sweep + ACLR

> *"Take one sweep, then run ACLR."*

```
sa_single_sweep()
sa_measure_aclr(channel_bw_hz=20e6, adjacent_offset_hz=20e6, alt_offset_hz=40e6)
```

Returns:

```json
{
  "channel_power_dbm": -8.2,
  "adjacent_lower_dbc": -47.1,
  "adjacent_upper_dbc": -46.8,
  "alternate_lower_dbc": -59.3,
  "alternate_upper_dbc": -58.9
}
```

## Step 4 — check the limit line

> *"Did the trace clear the CISPR 32 Class B mask?"*

```
sa_check_limits()
```

```json
{ "passed": true, "violations": [] }
```

## Step 5 — export

> *"Save the trace as JSON for the report and grab a screenshot."*

```
sa_save_trace_json(path="dut_5g2_aclr.json")
sa_save_screenshot(path="dut_5g2_aclr.png")
```

---

## What just happened

Five plain-English turns ran a full ACLR + limit-check + export sequence
against a CISPR 32 Class B mask, without you writing a single SCPI command.
The exported JSON drops straight into the `emc-precompliance` workflow,
where `mcp-emc-regulations` can cross-reference the result against the
correct standard variant.

- For more tools: [Tool reference](tools.md)
- For how this fits in the suite: [Architecture](architecture.md)
- For sibling MCPs that compose with this one: [eng-mcp-suite catalog](https://github.com/RFingAdam/eng-mcp-suite#whats-included)
