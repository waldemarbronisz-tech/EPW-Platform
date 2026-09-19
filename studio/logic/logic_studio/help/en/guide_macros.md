# Creating a macro and using it in several bays

1. **Select the piece of diagram** you want to wrap into a macro.
2. **Create a macro from the selection** (the selection's context menu)
   and give it a name. The boundary pins are created automatically from
   the wires crossing the selection boundary — see [Macro blocks and
   parameters](help:concept_macros) for the full explanation of where
   they come from.
3. **Place further instances** of the same macro from the block library
   (in the macros section) in other bays of the diagram — each instance
   is an independent visual copy of the same definition.
4. **Bind a property to a parameter** if different bays need different
   values (a different delay time, say) — without that, every instance
   shares the one value stored in the definition.
5. **Edit the definition** to change the logic inside the macro for ALL
   of its instances at once — open the macro for editing (double-click an
   instance, or use the navigation tree) and make the change once.
6. **Export/import the macro** as an `.epwmacro` file if you want to use
   it in another project.

See also the full explanation of the concepts in [Macro blocks and
parameters](help:concept_macros).
