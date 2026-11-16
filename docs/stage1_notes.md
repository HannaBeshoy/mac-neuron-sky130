# Stage 1 notes: method and what the numbers mean

## Method

**Models.** The transistors are the 1.8 V devices of the SKY130 process,
simulated with the BSIM4 models that the foundry publishes. `sim/models_*.lib`
loads only the two devices I use. Three corners are simulated: typical
transistors at 1.80 V and 25 °C, slow transistors at 1.60 V and 100 °C, and
fast transistors at 1.95 V and -40 °C. These are the three conditions for
which the foundry cell library is also characterised, so stage 2 can compare
like with like.

**Transfer curve.** Input a is swept from 0 V to the supply in 2 mV steps
while the other input is held at the level that lets input a control the
output (supply for NAND2, ground for NOR2).

- The switching threshold is the point where output equals input.
- V_IL and V_IH are the two points where the slope of the curve is -1.
  Between them the cell amplifies noise, outside them it reduces it.
- Noise margins: NM_L = V_IL - V_OL and NM_H = V_OH - V_IH.

**Delay.** The input gets one rising and one falling edge of 50 ps. Delay is
measured from the input crossing half the supply to the output crossing half
the supply. Edge times are measured between 20 % and 80 %. Five load
capacitors from 1 fF to 20 fF are used, and a straight line
`delay = t0 + 0.69 · R · C` is fitted. This is the first-order RC model of a
switching gate: R is the equivalent resistance of the conducting transistors
and t0 is the delay caused by the cell's own capacitance and the input edge.

**Energy.** The supply current is integrated over one full cycle of the
output and multiplied by the supply voltage. Charging a capacitor C through
any resistance takes C · Vdd² from the supply, half stored and half lost as
heat, and the stored half is lost on the discharge. So the load alone
explains C · Vdd² per cycle. What is measured above that is the cell's own
capacitance and the current that flows directly from supply to ground while
both transistor types conduct during the input edge.

## What the results show

1. **The threshold is below half the supply.** The inverter switches at
   0.79 V, not 0.90 V. The n-channel transistor is stronger than the
   p-channel one even though the p-channel is wider (1.00 µm against
   0.65 µm): holes move more slowly than electrons, and the p-channel device
   here is the high-threshold type. The fitted resistances say the same:
   4.2 kΩ pulling down, 9.7 kΩ pulling up. A balanced inverter would need a
   p-channel width of roughly 2.3 times what it has now.
2. **Noise margins are healthy.** 0.69 V low and 0.93 V high at 1.8 V, both
   above a third of the supply at every corner. The unequal margins follow
   from the low threshold.
3. **Series transistors cost drive on their own side only.** NAND2 pulls
   down through two n-channel devices in series: 6.5 kΩ against 4.2 kΩ for
   the inverter, while its pull-up stays at 9.7 kΩ. NOR2 pulls up through
   two p-channel devices in series: 20.3 kΩ against 9.7 kΩ. Because the
   p-channel side is already the weak one, NOR2 is the slowest cell
   (112 ps rise delay at 5 fF against 60 ps for the inverter). This is why
   cell libraries and synthesis tools prefer NAND to NOR.
   The series resistance of NAND2 is less than twice that of one transistor
   (1.55 times), because the transistor next to ground has its full gate
   voltage and the input edge is not instant.
4. **Corners move the delay by about a factor of two to three.** Inverter
   fall delay at 5 fF: 22 ps fast, 32 ps typical, 53 ps slow. A design has
   to meet its clock period at the slow corner and its hold times at the
   fast corner.
5. **Energy follows C · Vdd².** With 5 fF the inverter takes 21.3 fJ per
   cycle, of which the load explains 16.2 fJ. Going from 1 fF to 20 fF adds
   C · Vdd² within 10 % (checked by a test). The remaining 5 fJ corresponds
   to about 1.6 fF of the cell's own capacitance plus the direct current.

## Limits

- Source and drain areas are estimates. After layout, real diffusion areas
  and wire capacitance are known, and the delay without load (t0) will
  change. The resistances depend much less on this.
- Only input a is characterised for the two-input cells. Input b sits next
  to the supply rail in the series stack and will be slightly different.
- One input edge time (50 ps) is used. A cell library gives delay as a
  table over input edge time and load; stage 2 looks at that.
- No variation between transistors on the same chip (mismatch) is
  simulated, only the global corners.

## Link to my courses

- Electronics: the transistor as a switch with on-resistance, RC charging,
  the 0.69 · RC time to reach half the final value.
- Digital design: logic levels, noise margins, fan-out as capacitive load,
  propagation delay.
- Programmable logic devices: timing at slow and fast corners is what the
  FPGA timing report does for me automatically; here I produce the cell
  numbers that such a report is built from.
