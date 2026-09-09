"""Analog input channel configuration and raw -> engineering scaling.

Headless (no PyQt import) on purpose: this is shared, unit-testable logic
between the Analog Inputs page (epw_os/gui/pages/page_analog_inputs.py)
and the persisted per-channel config in ProjectManager. Neither of those
two needs to depend on the other for the constants/formula to agree.

Signal types:
  - "4-20mA" / "0-10V" / "0-3.3V ADC (raw)": the tag's raw value is linearly
    scaled into engineering units using the configured raw/engineering
    ranges.
  - SIGNAL_TYPE_READY: the tag's raw value already *is* the engineering
    value (e.g. a driver - or, today, the simulator - that already did the
    conversion) - shown as-is, no scaling, ranges are irrelevant and stay
    hidden in the config dialog.

Deliberately no Modbus/register format assumptions here - that's a real
driver's job later; this only defines the *software* scaling contract a
driver's raw tag value is expected to satisfy.
"""

SIGNAL_TYPE_4_20MA = "4-20mA"
SIGNAL_TYPE_0_10V = "0-10V"
SIGNAL_TYPE_0_3V3_ADC = "0-3.3V ADC (raw)"
SIGNAL_TYPE_READY = "Wartość gotowa (bez przeliczania)"

# Display order in the config dialog's dropdown.
SIGNAL_TYPES = [
    SIGNAL_TYPE_4_20MA,
    SIGNAL_TYPE_0_10V,
    SIGNAL_TYPE_0_3V3_ADC,
    SIGNAL_TYPE_READY,
]

# Seeded into the config the moment the operator picks a scaled signal
# type - a starting point (these are the standard wire ranges for each
# signal type), not an enforced limit; still freely editable afterwards.
DEFAULT_RAW_RANGE = {
    SIGNAL_TYPE_4_20MA: (4.0, 20.0),
    SIGNAL_TYPE_0_10V: (0.0, 10.0),
    SIGNAL_TYPE_0_3V3_ADC: (0.0, 3.3),
}

DEFAULT_DECIMALS = 1


def needs_scaling(signal_type: str) -> bool:
    """False only for the passthrough ('ready value') signal type."""
    return signal_type != SIGNAL_TYPE_READY


def default_channel_config() -> dict:
    """A channel with no persisted config yet behaves as a plain
    passthrough - shows the tag's raw value, unitless, one decimal."""
    return {
        "signal_type": SIGNAL_TYPE_READY,
        "raw_min": 0.0,
        "raw_max": 100.0,
        "eng_min": 0.0,
        "eng_max": 100.0,
        "unit": "",
        "decimals": DEFAULT_DECIMALS,
    }


def normalize_config(config: dict) -> dict:
    """Fill in any missing keys with defaults - config dicts loaded from an
    older/partial project.json should never KeyError the page."""
    merged = default_channel_config()
    if config:
        merged.update(config)
    return merged


def scale_to_engineering(raw_value: float, raw_min: float, raw_max: float,
                          eng_min: float, eng_max: float) -> float:
    """Linear map: raw_min..raw_max -> eng_min..eng_max.

    A degenerate span (raw_max == raw_min, a config typo) returns eng_min
    instead of raising ZeroDivisionError - a bad config should show a
    number, not crash the page.
    """
    span = raw_max - raw_min
    if span == 0:
        return eng_min
    ratio = (raw_value - raw_min) / span
    return ratio * (eng_max - eng_min) + eng_min


def compute_display_value(raw_value, config: dict):
    """The value to show (before formatting/unit), in engineering units
    unless the channel is a passthrough. None in -> None out (no reading
    yet / unknown tag)."""
    if raw_value is None:
        return None
    cfg = normalize_config(config)
    raw_value = float(raw_value)
    if not needs_scaling(cfg["signal_type"]):
        return raw_value
    return scale_to_engineering(
        raw_value,
        float(cfg["raw_min"]), float(cfg["raw_max"]),
        float(cfg["eng_min"]), float(cfg["eng_max"]),
    )


def format_display_value(raw_value, config: dict) -> str:
    """Formatted number only (no unit) - callers append cfg['unit']
    themselves, since some also show the unit in its own table column."""
    value = compute_display_value(raw_value, config)
    if value is None:
        return "-"
    decimals = int(normalize_config(config)["decimals"])
    return f"{value:.{decimals}f}"
