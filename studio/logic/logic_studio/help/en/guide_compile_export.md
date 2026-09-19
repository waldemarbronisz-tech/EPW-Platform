# Compiling and exporting the logic to EPW-OS

1. **Compile** (F5, or "Compile" from the Logic menu). The compiler
   checks the project (errors and warnings go to the results panel) and
   builds the blocks' execution order.
2. **Fix the errors.** Red entries in the results panel are errors — the
   compile has to pass without them before an export means anything.
   Yellow ones are warnings (an unfinished wire, an internal signal
   written but never read) — worth reading, but they do not block the
   export.
3. **Export the runtime** ("Export Runtime" from the Logic menu) — writes
   the compiled logic in the format EPW-OS loads and executes on site.
4. **Export the signal list / a PDF**, if you need them for design
   documentation or for agreeing an interface with another team —
   separate commands in the Project menu ("Export signals...", "Export to
   PDF...").

The runtime export reflects EXACTLY what the editor shows at the moment
of export — including disabled blocks (see [Disabled blocks and
forces](help:concept_disabled_blocks)) and the labels of analog points
and I/O addresses.
