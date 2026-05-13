# mcp-rs-spectrum-analyzer

**Drive Rohde & Schwarz spectrum and signal analyzers from any MCP-compatible AI client.**
**TCP or VISA — 62 tools spanning frequency, bandwidth, markers, measurements, traces, limits, and templates.**

---

## What it is

`mcp-rs-spectrum-analyzer` is a [Model Context Protocol](https://modelcontextprotocol.io)
server that automates spectrum and signal analyzers over SCPI. Primary target
is the R&S FSW / FSVA3000 / FSV3000 / FPL1000 family with vendor-specific
result parsing; a common SCPI core also covers Keysight, Rigol, Siglent,
Anritsu, and Tektronix analyzers (~95% command-set overlap).

Transport is either raw TCP/IP socket (no VISA install needed) or PyVISA for
GPIB / USB-TMC / HiSLIP.

## Install

```bash
uv pip install -e .
# Optional: VISA support for GPIB/USB/HiSLIP
uv pip install -e ".[visa]"
```

## First call

=== "MCP"

    Add to `claude_desktop_config.json`:

    ```json
    {
      "mcpServers": {
        "spectrum-analyzer": {
          "command": "spectrum-analyzer-mcp"
        }
      }
    }
    ```

    Then ask your assistant:

    > *"Connect to the SA at 192.168.1.100, find the peak between 1–2 GHz, and run a channel-power measurement."*

=== "Python"

    ```python
    import asyncio
    from spectrum_analyzer_mcp.driver import SpectrumAnalyzerDriver

    async def main():
        async with SpectrumAnalyzerDriver("192.168.1.100", 5025) as sa:
            await sa.set_center_span(1e9, 100e6)
            print(await sa.peak_search())

    asyncio.run(main())
    ```

## Where to next

- [Tool reference](tools.md) — every MCP tool with arguments
- [Usage examples](usage.md) — an EMC pre-compliance walkthrough
- [Architecture](architecture.md) — how this MCP fits inside eng-mcp-suite

---

!!! note "Part of eng-mcp-suite"
    This MCP server is part of [eng-mcp-suite](https://github.com/RFingAdam/eng-mcp-suite) —
    an umbrella of engineering MCP servers across RF, EMC, PCB, signal
    integrity, EM simulation, and lab test.
