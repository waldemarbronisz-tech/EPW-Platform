# 9.6 Drawing Layers and Why a Symbol Never Falls Under a Wire

Drawing on the schematic happens in fixed layers, always in the same order: wires and junctions, then symbols/meters/panels, then labels (a separate pass AFTER every symbol), and selection and transform handles on top of everything.

A label is drawn in a SEPARATE, later pass after every symbol precisely so one object's label never falls under a different, neighboring object's symbol - the objects' own array order does not matter here, the label layer is always entirely above the symbol layer.
