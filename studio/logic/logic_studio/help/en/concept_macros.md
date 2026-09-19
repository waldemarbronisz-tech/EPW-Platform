# Macro blocks and parameters

A macro block lets you wrap a piece of a diagram into a single, reusable
block — useful for repeating arrangements (a "motor start sequence", say)
that would otherwise have to be copied and pasted separately into every
place they are needed.

## Wrapping a fragment into a macro

Select the blocks that are to make up the macro and use the "create macro
from selection" command (the selection's context menu). This produces a
new macro definition together with its first instance, in place of the
old selection.

## Where the boundary pins come from

**This is the most common misunderstanding**: the pins on a macro block's
edge are NOT something you have to add by hand. They are created
automatically from every wire that CROSSED the selection boundary at the
moment the macro was made — one end inside the selected blocks, the other
outside. Each such wire becomes one boundary pin of the macro, with the
direction the signal was flowing in. If it turns out afterwards that a
pin is missing (because something was not connected before you selected,
say) or that one is superfluous, boundary pins can be edited later,
without building the macro again from scratch.

## Binding a setting to a parameter

A macro parameter lets each INSTANCE of the same macro carry its own
value for some property (a delay time that differs per bay, for example)
instead of one value shared by every copy. A property of a block INSIDE
the macro definition is bound to a macro parameter — from then on each
instance asks for its own value of that parameter instead of inheriting
the value stored in the definition.

See also: [Creating a macro and using it in several
bays](help:guide_macros).
