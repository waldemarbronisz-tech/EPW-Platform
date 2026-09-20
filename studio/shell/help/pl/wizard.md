# Kreator urządzenia

**Plik → Kreator urządzenia.** Przeprowadza przez kroki 1–4
z [drogi projektu](help://workflow) w kolejności, w jakiej projekt ich
potrzebuje. Nic nie jest zapisywane, dopóki nie naciśniesz **Zakończ**.

## 1. Informacje o projekcie

Nazwa (wymagana — bez niej kreator nie idzie dalej), autor, opis.

## 2. Skład urządzenia

Zaznaczasz moduły, które ten sterownik ma. Moduły już obecne w projekcie
zostają zaznaczone; **usuwać moduł trzeba w dziale [Skład
urządzenia](help://devices)**, nie tutaj.

## 3. Lokalizacje

Kod (tylko litery A–Z i cyfry, np. `KOT` na kotłownię) plus opis.
Kreator od razu mówi, jeśli kod ma niedozwolony znak albo się powtarza.

## 4. Karty wejść/wyjść

Jeden wiersz na fizyczny moduł: id, model, zaznaczone rodzaje kanałów
z licznikami, adres Modbus, lokalizacja. Karta mająca DI **i** AI to
jeden wiersz z dwoma zaznaczeniami, nie dwa wiersze.

Sprawdzane od razu: puste id, kropka albo spacja w id, powtórzone id,
karta bez żadnego rodzaju kanału, powtórzony adres Modbus.

## 5. Podsumowanie i co dalej

Zestawienie: ile modułów, lokalizacji, kart i ile **punktów** powstanie.
Poniżej lista następnych kroków w drzewie — rejestr punktów, aparaty,
alarmówka/zabezpieczenia, ekrany, logika — i przypomnienie, że kreator
**nie zapisuje pliku**: zapis jest Twój, z górnego paska.
