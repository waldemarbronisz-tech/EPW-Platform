Bufor przepisuje wejście na wyjście bez zmiany (Out = In1). Nie wnosi
opóźnienia o cykl skanu — jest liczony w kolejności topologicznej jak
każdy inny blok.

### Kiedy się przydaje

- **Czytelność**: jako punkt, z którego rozchodzi się kilka przewodów
  do różnych części schematu, zamiast prowadzić je wszystkie z jednego
  pinu bloku wejściowego.
- **Miejsce na późniejszą logikę**: wstaw bufor tam, gdzie spodziewasz
  się kiedyś warunku — wymiana na [AND](help:block:logic.and) nie
  wymaga przerysowania.
- **Etykieta**: przewód z bufora może dostać etykietę i płynąć dalej
  bez rysowania — patrz [Etykiety, znaczniki i bity
  urządzenia](help:concept_labels).
