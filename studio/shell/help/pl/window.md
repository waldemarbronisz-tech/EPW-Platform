# Okno Studia

## Lewa kolumna

Od góry: **LISTA URZĄDZEŃ** (obiekt i jego sterowniki — patrz
[Obiekt](help://site)), pod nią **drzewo projektu** aktywnego
sterownika.

Drzewo ma stałą strukturę, niezależnie od tego, co jest wypełnione:

- **PROJEKT** — Informacje, Skład urządzenia
- **KONFIGURACJA** — Lokalizacje, Karty, Rejestr punktów, Rejestr
  aparatów, Schemat synoptyczny, Logika, MQTT, Powiązania obiektu,
  Notatki serwisowe — w kolejności, w jakiej projekt ich potrzebuje:
  każdy dział po tych, na których się opiera
- **ALARMÓWKA** — Strefy, Linie dozorowe, Użytkownicy
- **ZABEZPIECZENIA** — Elektryczne, Procesowe
- **STEROWNIK** — Połączenie, Test zabezpieczeń
- **Pomoc**

Gałęzie modułów spoza [składu urządzenia](help://devices) są ukryte.

## Gdzie masz niezapisane zmiany

Dział, w którym coś edytowałeś, jest **czerwony z gwiazdką**
(`Lokalizacje *`) aż do zapisania projektu. Sterownik na liście urządzeń
oznacza się tak samo. To jedyne miejsce, w którym widać „co jeszcze nie
jest na dysku" bez otwierania każdego działu po kolei.

Korzeń drzewa nosi nazwę projektu — **dwuklik zmienia ją w miejscu**, to
samo pole co w [Informacjach o projekcie](help://info).

## Paski

**Górny pasek jest stały** i dotyczy zawsze **projektu**: Nowy, Otwórz,
Zapisz, Zapisz jako, Cofnij, Ponów, Pomoc. Działa na każdej gałęzi —
także tam, gdzie nie ma żadnego edytora.

**Pasek kontekstowy** pod nim należy do aktywnego działu. W Ekranach
i w Logice są tam własne narzędzia tych edytorów, razem z cyklem życia
ich własnych dokumentów.

## F1 — pomoc kontekstowa

W dowolnym momencie **F1** otwiera pomoc od razu na temacie działu,
w którym jesteś. Nie trzeba go szukać na liście.

## Język

**Ustawienia → Język** przełącza interfejs i tę pomoc. Klucze i wartości
zapisane w projekcie się nie zmieniają — zmienia się tylko to, co widzisz.
