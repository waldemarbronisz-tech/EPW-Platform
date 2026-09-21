# 5.7 Boundary Point: Source and Sink of the Installation

A boundary point represents the spot where the installation on this screen meets the outside world: a utility connection, a well, a discharge point. It is the only symbol with a direction field: Boundary Direction, SOURCE or SINK, plus Boundary Medium (ELECTRICAL/WATER/VENTILATION).

Two SOURCE boundary points tied into one net is a warning (`MULTIPLE_SOURCES`, [5.6](help://synoptic/sch-net-validation)) - two independent supplies joined together is a real installation concern (e.g. two sources running in parallel with no synchronization), worth catching at the screen-design stage.

A boundary point's label and sub-label are this object's own designation/description (not separate fields), and its single terminal sits on the side named by its Boundary Port Side field (top/bottom/left/right) - unlike every other symbol, whose terminals sit at fixed positions from the registry ([6.2](help://synoptic/sym-terminals)), this one's terminal side is chosen per instance.
