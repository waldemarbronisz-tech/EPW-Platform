# Logic gates: how to read them and what they are for

A logic gate computes one TRUE/FALSE value from one, two, three or four
input values. The result is ready in the same scan (no delay - see [The
scan cycle](help:concept_scan_cycle)); a gate has no memory, its output
depends only on what is on its inputs **now**. Memory comes from
[latches](help:concept_memory_edges), time from [timers](help:concept_timers).

Every gate's page in the Block catalog carries a **truth table**, an
**animation** of the diagram in simulation (green wires and ports = TRUE,
black = FALSE) and **examples of use** from real installations.

## The family

| Gate | Output TRUE when... | Typical use |
|---|---|---|
| [AND](help:block:logic.and) ([AND-3](help:block:logic.and3), [AND-4](help:block:logic.and4)) | **all** inputs TRUE | permission: every condition at once |
| [OR](help:block:logic.or) ([OR-3](help:block:logic.or3), [OR-4](help:block:logic.or4)) | **any** input TRUE | common alarm, stop from several places |
| [NOT](help:block:logic.not) | the input is FALSE | a normally-closed contact, negating a condition |
| [NAND](help:block:logic.nand) (-3, -4) | **not all** inputs TRUE | "not both at once" interlock |
| [NOR](help:block:logic.nor) (-3, -4) | **no** input TRUE | "all well" lamp |
| [XOR](help:block:logic.xor) | inputs **differ** | feedback mismatch, two-way switching |
| [XNOR](help:block:logic.xnor) | inputs **equal** | command agrees with feedback |
| [BUFFER](help:block:logic.buffer) | the input is TRUE (pass-through) | a fan-out point, room for later logic |

## Rules common to every gate

1. **An unconnected input is FALSE.** An AND with one empty input never
   gives TRUE; an OR with an empty input simply does not see it. The
   compiler warns about unconnected inputs - do not ignore it.
2. **A stub** (2+ input gates only) takes an input out of the
   computation: an AND-4 with one stubbed input computes like an AND-3.
   Use it deliberately where the site has no such condition - see [Input
   stub, free wire end, label](help:concept_stubs).
3. **More than four inputs**: a cascade (one gate's output into another -
   AND(AND(a,b,c,d), AND(e,f)) is an AND of six) or a
   [macro](help:concept_macros) with a telling name.
4. **Negation on an input**: there is no "inversion bubble" on a pin -
   put a [NOT](help:block:logic.not) in front of the input. With several
   negations consider NOR/NAND, which often replace NOT + OR/AND with one
   block.
5. **A signal from the panel and from the logic**: an IN bit (written by
   the panel, a synoptic push button, REST) is read with the "Bit input
   (internal)" block and fed to a gate like any other signal; a gate's
   result is written with "Bit output (internal)" to an OUT bit - that
   bit is, for instance, an apparatus's permission on the controller.
   See [Labels, markers and device bits](help:concept_labels).

## Choosing a gate - three questions

- Should the result be TRUE when **all** conditions hold (AND), or when
  **any** does (OR)?
- Am I interested in the condition being **met** or **not met**? If not
  met - NAND/NOR/NOT instead of an extra negation block.
- Am I comparing two signals with each other (XOR: different, XNOR:
  equal)?

When **time** joins the conditions ("for 2 s", "after 5 s", "for 200 ms")
or **memory** ("until cleared"), a gate is not enough - reach for
[timers](help:concept_timers) and [latches](help:concept_memory_edges).
Ready, proven combinations of these blocks are in [Typical control
circuits](help:guide_typical_circuits).
