# Power Quality: a Simulation Sandbox

The Power Quality page is a **simulation tool**, not a measurement
page — a persistent amber banner at the top says so. The waveforms and
sliders (Voltage Ampl., Current Ampl., Frequency, Noise %, Harmonics %)
generate synthetic sine waves for demonstration and training. They have
no connection to any real voltage or current signal, unlike the Main
View measurement panel or Digital/Analog Inputs.

The two tags the sliders write (Sim.Voltage, Sim.Frequency) are
recorded by Historian with quality **SIMULATED**, exactly like the Main
View measurement panel — see [What Historian Records](help://hist_what).
