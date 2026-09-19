def register_builtin_blocks():
    """Explicitly imports and registers all builtin blocks during startup."""
    import shared.logic.blocks.io_blocks
    import shared.logic.blocks.analog_io
    import shared.logic.blocks.logic_gates
    import shared.logic.blocks.timers
    import shared.logic.blocks.counters
    import shared.logic.blocks.memory
    import shared.logic.blocks.math_blocks
    import shared.logic.blocks.comparators
    import shared.logic.blocks.virtual_io
    import shared.logic.blocks.system_signals
    import shared.logic.blocks.constants
    import shared.logic.blocks.edges
    import shared.logic.blocks.analog_processing
    import shared.logic.blocks.documentation
