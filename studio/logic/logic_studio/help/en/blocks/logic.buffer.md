The buffer passes its input to its output unchanged (Out = In1). It adds
no scan delay - it is evaluated in topological order like any block.

### When it helps

- **Readability**: a point from which several wires fan out to different
  parts of the diagram, instead of running them all from one input
  block's pin.
- **Room for later logic**: put a buffer where you expect a condition
  one day - swapping it for an [AND](help:block:logic.and) needs no
  redrawing.
- **A label**: a wire from the buffer can take a label and continue
  without being drawn - see [Labels, markers and device
  bits](help:concept_labels).
