"""SCPI command dialects for different instrument vendors.

SCPI is highly standardized, so most commands are identical across vendors.
This module captures the small differences in command syntax, default ports,
and behavioral quirks.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SCPIDialect:
    """SCPI command dialect for a specific vendor.

    Default values match the IEEE 488.2 / SCPI-99 standard commands
    which work across all major vendors.
    """

    # Vendor identification
    vendor_name: str = "Generic"

    # Network defaults
    default_port: int = 5025

    # Frequency
    cmd_center_freq: str = "SENS:FREQ:CENT"
    cmd_span: str = "SENS:FREQ:SPAN"
    cmd_start_freq: str = "SENS:FREQ:STAR"
    cmd_stop_freq: str = "SENS:FREQ:STOP"
    cmd_freq_step: str = "SENS:FREQ:CENT:STEP"
    cmd_full_span: str = "SENS:FREQ:SPAN:FULL"

    # Amplitude
    cmd_ref_level: str = "DISP:TRAC:Y:RLEV"
    cmd_attenuation: str = "INP:ATT"
    cmd_preamp: str = "INP:GAIN:STAT"
    cmd_scale: str = "DISP:TRAC:Y:PDIV"

    # Bandwidth
    cmd_rbw: str = "SENS:BAND:RES"
    cmd_rbw_auto: str = "SENS:BAND:RES:AUTO"
    cmd_vbw: str = "SENS:BAND:VID"
    cmd_vbw_auto: str = "SENS:BAND:VID:AUTO"
    cmd_sweep_time: str = "SENS:SWE:TIME"
    cmd_sweep_time_auto: str = "SENS:SWE:TIME:AUTO"

    # Trace
    cmd_trace_data: str = "TRAC:DATA? TRACE{n}"
    cmd_trace_mode: str = "DISP:TRAC{n}:MODE"
    cmd_detector: str = "SENS:DET{n}"
    cmd_averaging_state: str = "SENS:AVER:STAT"
    cmd_averaging_count: str = "SENS:AVER:COUN"

    # Markers
    cmd_marker_state: str = "CALC:MARK{n}:STAT"
    cmd_marker_x: str = "CALC:MARK{n}:X"
    cmd_marker_y: str = "CALC:MARK{n}:Y"
    cmd_marker_max: str = "CALC:MARK{n}:MAX"
    cmd_marker_next_peak: str = "CALC:MARK{n}:MAX:NEXT"
    cmd_marker_min: str = "CALC:MARK{n}:MIN"
    cmd_marker_center: str = "CALC:MARK{n}:CENT"
    cmd_delta_state: str = "CALC:DELT{n}:STAT"
    cmd_marker_bwidth_state: str = "CALC:MARK{n}:FUNC:BWID:STAT"
    cmd_marker_bwidth_ndb: str = "CALC:MARK{n}:FUNC:BWID:NDB"
    cmd_marker_bwidth_result: str = "CALC:MARK{n}:FUNC:BWID:RES?"

    # Sweep
    cmd_continuous: str = "INIT:CONT"
    cmd_single: str = "INIT:IMM"
    cmd_trigger_source: str = "TRIG:SOUR"
    cmd_trigger_level: str = "TRIG:LEV"

    # Measurements
    cmd_meas_select: str = "CALC:MARK:FUNC:POW:SEL"
    cmd_meas_result: str = "CALC:MARK:FUNC:POW:RES?"
    cmd_ch_bw: str = "SENS:POW:ACH:BWID:CHAN1"
    cmd_adj_bw: str = "SENS:POW:ACH:BWID:ACH"
    cmd_adj_spacing: str = "SENS:POW:ACH:SPAC"
    cmd_obw_percent: str = "SENS:POW:ACH:BWID:PCT"

    # System
    cmd_error: str = "SYST:ERR?"
    cmd_preset: str = "SYST:PRES"

    # Behavioral flags
    implicit_sense_root: bool = False  # Keysight: SENS: is implicit
    silent_coercion: bool = False  # Keysight: silently coerces out-of-range
    terminator: str = "\n"

    # Additional vendor-specific next-peak commands
    next_peak_commands: tuple[str, ...] = field(default_factory=lambda: ("CALC:MARK{n}:MAX:NEXT",))


# =============================================================================
# Pre-built vendor dialects
# =============================================================================

RS_DIALECT = SCPIDialect(
    vendor_name="Rohde & Schwarz",
    default_port=5025,
)

KEYSIGHT_DIALECT = SCPIDialect(
    vendor_name="Keysight",
    default_port=5025,
    implicit_sense_root=True,
    silent_coercion=True,
    cmd_preamp="POW:GAIN",
)

RIGOL_DIALECT = SCPIDialect(
    vendor_name="Rigol",
    default_port=5555,
    cmd_trace_data="TRAC:DATA? TRACE{n}",
)

SIGLENT_DIALECT = SCPIDialect(
    vendor_name="Siglent",
    default_port=5025,
)

ANRITSU_DIALECT = SCPIDialect(
    vendor_name="Anritsu",
    default_port=5025,
)

TEKTRONIX_DIALECT = SCPIDialect(
    vendor_name="Tektronix",
    default_port=5025,
)

# Lookup table: normalized manufacturer name -> dialect
VENDOR_DIALECTS: dict[str, SCPIDialect] = {
    "ROHDE&SCHWARZ": RS_DIALECT,
    "ROHDE & SCHWARZ": RS_DIALECT,
    "KEYSIGHT TECHNOLOGIES": KEYSIGHT_DIALECT,
    "KEYSIGHT": KEYSIGHT_DIALECT,
    "AGILENT TECHNOLOGIES": KEYSIGHT_DIALECT,
    "AGILENT": KEYSIGHT_DIALECT,
    "RIGOL TECHNOLOGIES": RIGOL_DIALECT,
    "RIGOL": RIGOL_DIALECT,
    "SIGLENT TECHNOLOGIES": SIGLENT_DIALECT,
    "SIGLENT": SIGLENT_DIALECT,
    "ANRITSU": ANRITSU_DIALECT,
    "TEKTRONIX": TEKTRONIX_DIALECT,
}


def detect_dialect(idn_manufacturer: str) -> SCPIDialect:
    """Detect SCPI dialect from *IDN? manufacturer string.

    Returns the generic SCPI dialect if manufacturer is not recognized.
    """
    key = idn_manufacturer.strip().upper()
    return VENDOR_DIALECTS.get(key, SCPIDialect())
