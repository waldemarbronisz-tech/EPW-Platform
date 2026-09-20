# Nowy sterownik, krok po kroku

Co zrobić, po kolei, ze sterownikiem świeżo zamontowanym w szafie. Każdy
krok prowadzi do strony, która tłumaczy go porządnie.

## 1. Sprawdź, co naprawdę pracuje

Pasek stanu, od lewej: tryb pracy, komunikacja, [wskaźnik
logiki](help://logic_state), stan alarmówki,
[wymuszenia](help://dio_force), zegar. Każdy problem startowy jest
zgłaszany w oknie przy uruchomieniu programu — przeczytaj je, zamiast
zamykać.

## 2. Wgraj na niego projekt

**Plik → Otwórz** — patrz [Wgranie projektu](help://proj_install).
Sterownik przebudowuje się według nowego pliku bez restartu, więc tą
samą drogą poprawia się projekt później.

## 3. Ustaw PIN-y

[Poziomy dostępu](help://al_three) to Operator i Engineer, każdy
z własnym PIN-em. Zmień je z domyślnych, zanim ktokolwiek inny dotknie
panelu — [Zmiana PIN-u](help://al_change_pin).

## 4. Daj alarmówce jej ludzi

**Ustawienia → Użytkownicy alarmówki** (Engineer) — osoby pochodzą
z projektu; tutaj nadajesz każdej **kod na klawiaturę**, a jeśli ma
sterować z Home Assistanta — **token zdalny**. Patrz [Użytkownicy
alarmówki](help://intr_users).

## 5. Przejdź linie

Zanim cokolwiek uzbroisz na serio: [tryb
testu](help://intr_walk_test) pokazuje, które linie naprawdę widzą
przechodzącego człowieka, nie podnosząc alarmu. Czujka, której nikt
nigdy nie przeszedł, to czujka niesprawdzona.

## 6. Sprawdź nadzory

[Nadzór zasilania](help://intr_power_supervision) — sieć i akumulator.
[Życie linii](help://intr_line_life) — linia zbyt długo cicha zostaje
oznaczona jako podejrzana.

## 7. Podepnij sygnalizator w logice

Sterownik nie steruje żadną syreną; wystawia stan. Patrz
[Sygnalizator](help://intr_sounder) i [Co widzi program
logiki](help://logic_signals). Nic nie zadźwięczy, dopóki nie narysujesz
tej linii.

## 8. Podłącz integracje

[MQTT](help://mqtt_what) do Home Assistanta, a jeśli ma on tym
sterownikiem **sterować** — [Sterowanie z Home
Assistanta](help://mqtt_commands).

## 9. Dopiero teraz uzbrajaj

[Uzbrajanie i rozbrajanie](help://intr_arming), a jeśli ludzie mają
chodzić wewnątrz przy czuwającym perymetrze — [dozór
nocny](help://intr_night).

## 10. Zostaw ślad

[Notatki serwisowe](help://dio_service_notes) to dziennik — co
zastałeś, co wymieniłeś, co zostało zrobione do połowy. Wpisów nie
edytuje się ani nie kasuje, a wracają do Studia razem z projektem.
