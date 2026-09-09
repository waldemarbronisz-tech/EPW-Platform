# Zabezpieczenia elektryczne a procesowe

**ZABEZPIECZENIA** w menu nawigacyjnym po lewej dzielą się na dwie
strony, na tyle różne, że nigdy nie mieszają się na jednym ekranie:

- **Elektryczne** — zabezpieczenia nadprądowe, zwarciowe, napięciowe i
  częstotliwościowe: nastawy w amperach, woltach, hercach i sekundach,
  odpowiadające numerom funkcji przekaźnika zabezpieczeniowego ANSI,
  jakich użyłby prawdziwy przekaźnik rozdzielnicy (27 Under Voltage,
  51 Time Overcurrent i tak dalej). Docelowo wykonywane sprzętowo,
  przez ADA01, niezależnie od tego komputera — dziś ta strona jest
  tabelą konfiguracji tych nastaw, nie ich żywą ewaluacją.
- **Procesowe** — prosty próg (górny i dolny, z histerezą i zwłoką) na
  istniejącym punkcie analogowym: temperatura, wilgotność, poziom,
  ciśnienie albo cokolwiek innego już podłączonego jako Wejście
  Analogowe. Ewaluowane na żywo, programowo, przez sam program, i
  wystawiające tag sygnałowy dla logiki do reakcji.

Obie strony, tak jak każda strona alarmowo-nadzorcza w tym programie,
wyłącznie *raportują*. Żadna z nich nie steruje bezpośrednio żadnym
wyjściem, syreną ani żadną akcją sprzętową — patrz
[Zabezpieczenia elektryczne](help://prot_electrical) i
[Zabezpieczenia procesowe](help://prot_process), co dokładnie każda z
nich robi z tym, co obserwuje.
