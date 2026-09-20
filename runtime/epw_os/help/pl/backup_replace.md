# Wymiana padniętego sterownika

Padła karta albo cały sterownik. Na półce jest zamiennik. Oto
kolejność.

## Zanim zaczniesz

Potrzebujesz **kopii zapasowej** (patrz [Kopia zapasowa tego
sterownika](help://backup_what)) i dostępu Engineer do zamiennika. Jeśli
kopii nie ma, nadal masz projekt — w Studiu albo w repozytorium — a cała
reszta musi zostać odtworzona z pamięci, czemu właśnie kopia zapasowa ma
zapobiegać.

## Kolejność

1. **Zamontuj zamiennik**, daj mu zasilanie i magistralę. Wstanie na
   projekcie, jaki miał, albo na żadnym.
2. **Odtwórz** — Ustawienia → Odtwórz z kopii zapasowej..., wskaż plik.
   Pokaże, co jest w kopii; potwierdź. Sterownik przebuduje się, bez
   restartu.
3. **Ustaw PIN-y dostępu** — Ustawienia → Zmień PIN. Zamiennik przy
   pierwszym starcie wygenerował sobie własne, losowe; nikt ich nie zna.
4. **Nadaj kod na klawiaturę każdej osobie** — Ustawienia → Użytkownicy
   alarmówki. Osoby już tam są: pochodzą z projektu. Brakuje tylko ich
   sekretów, a odtworzenie wypisało je po nazwisku.
5. **Wydaj tokeny zdalne** tym, którzy je mieli — to samo okno. Token
   pokazuje się raz. Wklej go do automatyzacji Home Assistanta tej
   osoby.
6. **Wpisz hasło do brokera MQTT** — Ustawienia → MQTT, jeśli ta
   instalacja z niego korzysta.
7. **Wydaj tokeny REST API**, jeśli Studio łączy się z tym
   sterownikiem.
8. **Sprawdź, co mówi panel**: wskaźnik logiki na pasku stanu, stan
   alarmówki, czy karty odpowiadają na magistrali. Co każdy z nich
   powinien pokazywać — [Nowy sterownik, krok po
   kroku](help://gs_first_steps).
9. **Przejdź linie**, jeśli coś po stronie alarmówki było ruszane —
   [tryb testu](help://intr_walk_test).
10. **Zapisz to** — [notatki serwisowe](help://dio_service_notes). Co
    padło, kiedy, co wymieniono, co nadano na nowo.

## Czego nie odzyskasz

Historii trendów oraz wpisów dziennika zapisanych na padniętej karcie po
wykonaniu kopii. Cała reszta — projekt, liczniki, stan uzbrojenia,
pamięć alarmu, bity retencyjne, dziennik do momentu kopii — jest
w pliku.

Co jest argumentem za robieniem kopii cyklicznie, a nie tylko przed
zmianami.
