# Sygnalizator

Ten sterownik **nie steruje żadną syreną**. Wystawia stan
sygnalizatora, a program logiki decyduje, na które wyjście to trafi —
patrz [Co widzi program logiki](help://logic_signals).

To jest celowe. Jedna syrena, dwie syreny, syrena plus lampa, syrena
przez stycznik, syrena, która nie może wyć przy pracującym agregacie —
to wszystko jest tym samym zadaniem, czyli schematem, zamiast pięcioma
opcjami w oknie konfiguracji.

## Cztery odczyty

| Sygnał | Znaczenie |
|---|---|
| `SEC.SYSTEM.SIREN_ACTIVE` | sygnalizator ma dźwięczeć **teraz** — to podpinasz do wyjścia |
| `SEC.SYSTEM.SIREN_TIME_LEFT` | ile sekund jeszcze wolno |
| `SEC.SYSTEM.STROBE_ACTIVE` | lampa, świeci od alarmu do skasowania pamięci |
| `SEC.SYSTEM.PANIC` | zadziałała linia napadowa i nikt tego jeszcze nie potwierdził |

Ten sam stan jest na tagach `Security.System.SirenActive`,
`.StrobeActive` i `.Panic`, więc widzi go też ekran i Home Assistant.

## Gaśnie sam

`SIREN_ACTIVE` przechodzi w fałsz po upływie skonfigurowanego czasu
sygnalizacji (**Studio → Strefy → Sygnalizator**; 0 = bez ograniczenia),
**podczas gdy alarm trwa dalej**. Syrena bez końca jest zwykle niezgodna
z miejscowymi przepisami o hałasie, a lampa i tak pokazuje, że coś się
wydarzyło.

## Wyciszenie to nie rozbrojenie

Przycisk **Wycisz** na stronie Przegląd zatrzymuje **dźwięk** i nic
więcej: strefa zostaje w ALARM, pamięć alarmu zostaje, lampa świeci
dalej. „Wyłącz hałas" i „sprawa jest załatwiona" to dwie różne decyzje,
często oddalone o kilkanaście minut. Ta druga to [skasowanie pamięci
alarmu](help://intr_alarm_memory).

Przycisk pojawia się tylko wtedy, gdy jest co wyciszać, wymaga poziomu
Operator i jest odmawiany komuś, kogo strefy nie obejmują tej, która
sygnalizuje. Home Assistant może zrobić to samo przez
[MQTT](help://mqtt_commands).

**Nowy** alarm dźwięczy znowu, nawet po wyciszeniu — ktoś wyciszył
poprzedni, a ta decyzja nie obejmuje świeżego włamania.

## Linia napadowa

Linia **napadowa** alarmuje w każdym stanie strefy, także przy dozorze
nocnym, i domyślnie **nie uruchamia syreny**: sens alarmu napadowego
polega na tym, że stojący nad tobą człowiek nie dowiaduje się, że go
nacisnąłeś. Sam alarm jest w pełni prawdziwy — pamięć się zatrzaskuje,
lampa się załącza, `PANIC` przechodzi w prawdę, wszystko trafia do
dziennika. Instalacja, która chce go słyszalnego, wyłącza to w Studiu.

`PANIC` kasuje się razem z pamięcią alarmu, a nie rozbrojeniem: znaczy
„ktoś to nacisnął i nikt tego jeszcze nie potwierdził".
