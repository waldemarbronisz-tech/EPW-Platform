# 4.6 MEASURED - Measurement Devices

MEASURED is an analog measurement input: temperature, pressure, flow. Fields: input (an AI channel address), unit (e.g. "°C"), rangeMin/rangeMax (the range, rangeMin must be less than rangeMax), format (e.g. "0.0" - the digit count after the dot matches the number of zeros in that text) and deadband (a dead band around the value, >= 0).

The editor has no live data, so the form's own preview shows the MIDDLE of the configured range (e.g. 0..400 previews as 200), formatted per the format field - never a made-up number.

The meter wizard ([7.1](help://synoptic/elem-meter)) only ever shows MEASURED devices, grouped by unit - which is why a device must exist and have the MEASURED behavior before it appears in the wizard's own picker list.
