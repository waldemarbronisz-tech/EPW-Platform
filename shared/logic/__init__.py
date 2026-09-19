"""Logic the whole platform shares: the block library (what a block
MEANS) and the execution engine that runs it.

Logic Studio draws and compiles with it; runtime executes the compiled
program on the controller with the same code, so a block cannot behave
one way in the editor's simulation and another on the device. The same
reasoning that put the project format in shared/project_format.py.
"""
