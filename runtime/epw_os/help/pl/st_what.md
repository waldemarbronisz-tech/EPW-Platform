# Topologia systemu: co jest realne, a co nie

Diagram oraz pole **Status** na najwyższym poziomie drzewa urządzeń
(RUNNING/ONLINE/OFFLINE) odzwierciedlają realny stan komunikacji z
DeviceManager — to samo źródło, z którego korzysta panel statusu
urządzeń w Main View.

Każde inne pole w panelu informacyjnym pod drzewem (CPU Load, Memory
Usage, Temperature, Firmware, Hardware Revision, Serial Number, Frames
RX/TX, CRC Errors, Timeouts, ...) nie ma dziś w systemie żadnego
żywego źródła. Zamiast pokazywać wiarygodnie wyglądającą, ale zmyśloną
liczbę, te pola pokazują **"Brak danych"** — to celowy placeholder, nie
błąd i nie brakująca konfiguracja.
