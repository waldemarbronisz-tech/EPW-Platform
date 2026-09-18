# Test zabezpieczeń

„Wewnętrzny Omicron": test zabezpieczenia to wymuszenie stanu, pomiar
czasu zadziałania i raport — na tej samej mechanice, co wymuszanie
w rejestrze punktów. Test wykonuje **sterownik**, nie Studio: Studio
tylko go uruchamia, śledzi i pokazuje raporty, które sterownik trzyma
u siebie (`protection_test_reports.json`).

**Zabezpieczenie procesowe.** Sterownik wymusza punkt analogowy ponad
górny próg, mierzy czas do zadziałania (`Process.<id>.Exceeded`)
i porównuje go z nastawioną zwłoką: zadziałanie przed zwłoką albo
wyraźnie po niej to FAIL. Potem wymusza wartość z powrotem w pasmo
i mierzy czas skasowania; na koniec zdejmuje wymuszenie. Zabezpieczenie
wyłączone albo już zadziałane nie jest testowane (BLOCKED).

**Aparat.** Sterownik wydaje komendę zmieniającą stan (OTWÓRZ, gdy
sprzężenie mówi „zamknięty", inaczej ZAMKNIJ) tą samą drogą, co
z panelu — z blokadami logiki i kontrolą bezpieczeństwa, więc
odrzucona komenda to BLOCKED, nie obejście. Mierzy czas do zmiany
sprzężenia, po czym komendą przeciwną przywraca stan i mierzy go
ponownie.

**Zasady.** Token Engineer; jeden test naraz; start, wynik i każde
wymuszenie w dzienniku audytowym (`PROTECTION_TEST_*`, `FORCE_*`).
Tor zabezpieczeniowy — wyłączniki, aparaty z oznaczeniem Q, wszystko,
co nie jest punktem projektu — nie podlega wymuszaniu, więc i temu
testowi. Stopnie zabezpieczeń elektrycznych ADA01 sprawdza się przy
szafce, weryfikatorem panelu (rampa pomiaru), nie stąd.

**Raporty.** Tabela pokazuje nastawy, pomiar (czas zadziałania,
skasowania, sprzężenia) i uzasadnienie wyniku; dwuklik otwiera kroki
testu z czasem. „Zapisz raporty CSV" zapisuje wszystkie raporty ze
sterownika do pliku — dowód do protokołu uruchomienia.
