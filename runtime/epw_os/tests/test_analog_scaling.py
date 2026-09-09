"""Tests for the Analog Inputs raw -> engineering scaling logic
(epw_os/core/analog_scaling.py) - headless, no PyQt involved."""

import pytest

from epw_os.core import analog_scaling as scal


def test_default_config_is_passthrough_no_unit_one_decimal():
    cfg = scal.default_channel_config()
    assert cfg["signal_type"] == scal.SIGNAL_TYPE_READY
    assert cfg["unit"] == ""
    assert cfg["decimals"] == 1


def test_needs_scaling_only_false_for_ready_value():
    assert scal.needs_scaling(scal.SIGNAL_TYPE_READY) is False
    for t in (scal.SIGNAL_TYPE_4_20MA, scal.SIGNAL_TYPE_0_10V, scal.SIGNAL_TYPE_0_3V3_ADC):
        assert scal.needs_scaling(t) is True


def test_ready_value_passes_through_unchanged():
    cfg = scal.normalize_config({"signal_type": scal.SIGNAL_TYPE_READY})
    assert scal.compute_display_value(22.3, cfg) == 22.3
    # Raw/engineering ranges are irrelevant for ready-value - even a wild
    # range must not affect the passthrough result.
    cfg["raw_min"], cfg["raw_max"], cfg["eng_min"], cfg["eng_max"] = 5, 6, 999, 1000
    assert scal.compute_display_value(22.3, cfg) == 22.3


def test_linear_scaling_4_20ma_to_0_100_percent():
    cfg = scal.normalize_config({
        "signal_type": scal.SIGNAL_TYPE_4_20MA,
        "raw_min": 4.0, "raw_max": 20.0,
        "eng_min": 0.0, "eng_max": 100.0,
    })
    assert scal.compute_display_value(4.0, cfg) == pytest.approx(0.0)
    assert scal.compute_display_value(20.0, cfg) == pytest.approx(100.0)
    assert scal.compute_display_value(12.0, cfg) == pytest.approx(50.0)


def test_linear_scaling_handles_inverted_engineering_range():
    # e.g. a 4-20mA level transmitter wired "full at 4mA, empty at 20mA"
    cfg = scal.normalize_config({
        "signal_type": scal.SIGNAL_TYPE_0_10V,
        "raw_min": 0.0, "raw_max": 10.0,
        "eng_min": 100.0, "eng_max": 0.0,
    })
    assert scal.compute_display_value(0.0, cfg) == pytest.approx(100.0)
    assert scal.compute_display_value(10.0, cfg) == pytest.approx(0.0)


def test_degenerate_raw_span_does_not_raise():
    cfg = scal.normalize_config({
        "signal_type": scal.SIGNAL_TYPE_4_20MA,
        "raw_min": 10.0, "raw_max": 10.0,
        "eng_min": 5.0, "eng_max": 50.0,
    })
    assert scal.compute_display_value(10.0, cfg) == 5.0  # falls back to eng_min


def test_compute_display_value_none_for_no_reading():
    assert scal.compute_display_value(None, scal.default_channel_config()) is None


def test_format_display_value_respects_decimals():
    cfg = scal.normalize_config({
        "signal_type": scal.SIGNAL_TYPE_4_20MA,
        "raw_min": 4.0, "raw_max": 20.0,
        "eng_min": 0.0, "eng_max": 100.0,
        "decimals": 2,
    })
    assert scal.format_display_value(12.0, cfg) == "50.00"


def test_format_display_value_dash_for_missing_reading():
    assert scal.format_display_value(None, scal.default_channel_config()) == "-"


def test_normalize_config_fills_missing_keys_from_partial_dict():
    cfg = scal.normalize_config({"unit": "°C"})
    assert cfg["unit"] == "°C"
    assert cfg["signal_type"] == scal.SIGNAL_TYPE_READY  # untouched keys default
    assert cfg["decimals"] == 1


def test_normalize_config_handles_none():
    cfg = scal.normalize_config(None)
    assert cfg == scal.default_channel_config()


def test_default_raw_range_defined_for_every_scaled_type():
    for t in (scal.SIGNAL_TYPE_4_20MA, scal.SIGNAL_TYPE_0_10V, scal.SIGNAL_TYPE_0_3V3_ADC):
        assert t in scal.DEFAULT_RAW_RANGE
        low, high = scal.DEFAULT_RAW_RANGE[t]
        assert low < high
    assert scal.SIGNAL_TYPE_READY not in scal.DEFAULT_RAW_RANGE


def test_signal_types_list_matches_the_four_specified_types():
    assert set(scal.SIGNAL_TYPES) == {
        "4-20mA", "0-10V", "0-3.3V ADC (raw)", "Wartość gotowa (bez przeliczania)",
    }
