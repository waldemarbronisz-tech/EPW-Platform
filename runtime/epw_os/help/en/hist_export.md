# Exporting Historical Data

Available from **Tools → Export Historical Data...**, at every access
level.

## Steps

1. Set the **From** and **To** date range — the calendar opens with the
   button next to each field.
2. "All tags" is checked by default. Uncheck it to pick specific tags
   from the list.
3. Click **Export** and choose a CSV file.

The CSV file contains the columns: Timestamp, Tag, Value, Quality — in
local computer time (data in the database is stored in UTC and
converted to local time only at export time). If there's no data in the
selected range, the program tells you instead of creating an empty
file.

If the exported range includes any simulated values (Quality =
SIMULATED — see [What Historian Records](help://hist_what)), the
dialog and the completion message both say so explicitly, with a count.
The Quality column itself lets you filter or exclude them in whatever
tool opens the CSV afterwards.
