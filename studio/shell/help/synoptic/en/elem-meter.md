# 7.1 Meter

NOTE: there are TWO different "meters" in this editor. The static SCADA symbol "Meter (SCADA)" from the library is plain graphics with no rows and no state of its own - like any other symbol. This chapter covers the SECOND, dynamic Meter element (a toolbar button), built from rows.

A meter has any number of rows; each row either points at a MEASURED device (unit, format and the preview value - the middle of the range - always come FROM the device, never copied onto the row), or is a manual row with its own value and unit typed directly. A meter's height is ALWAYS computed from its row count, whether it has a title, and its font size - there is no height field to set by hand.

The measurement-picker wizard (the Kreator... button) shows ONLY MEASURED devices, grouped by unit - if the list is empty, the project has no MEASURED device yet (see [4.6](help://synoptic/dev-measured) and [chapter 11](help://synoptic/ts-meter-wizard-empty)).

A row pointing at a device that does not exist, or that is not itself MEASURED, is marked with the MISSING color instead of throwing an exception.
