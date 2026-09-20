# Sterowanie z Home Assistanta

Łącze MQTT nie jest już podglądem w jedną stronę. Home Assistant może
**uzbrajać** alarmówkę (w pełni albo nocą), **rozbrajać** ją,
**kasować** alarm, **wyciszać** sygnalizator, zmieniać **nastawy**
zabezpieczeń i wydawać **komendy** aparatom.

[Wymuszeń](help://dio_force) celowo nie ma na tej liście — wymuszenie
jest narzędziem kogoś stojącego przy szafie, trzymanym przy życiu jego
obecnością.

## Kto ma prawo

**Home Assistant ma jedno konto MQTT.** Wszyscy klikają w HA, ale broker
widzi zawsze tego samego klienta i nie odróżni dwóch osób. Dlatego
tożsamość jedzie **w treści wiadomości**: własny **token zdalny** każdej
osoby, wydawany na tym panelu i pokazywany raz — patrz [Użytkownicy
alarmówki](help://intr_users).

Uprawnienia są potem dokładnie panelowe: poziom osoby i strefy, którymi
może operować, sprawdzane przez te same managery, a nie przez drugi
zestaw reguł, który mógłby się rozjechać.

## Co jest odrzucane i dlaczego

| Odrzucane | Dlaczego |
|---|---|
| wiadomość **retained** | broker odtwarza ją każdemu, kto się połączy, w tym temu sterownikowi po zaniku zasilania — „rozbrój" wysłane raz rozbrajałoby obiekt po każdym restarcie |
| nie-JSON albo brak identyfikatora komendy | nie ma czego zidentyfikować ani na co odpowiedzieć |
| znacznik czasu starszy niż 120 s | przechwycona wiadomość jest bezużyteczna minutę później |
| nieznany token, osoba wyłączona albo token należący do kogo innego, niż mówi wiadomość | podszycie się |
| za niski poziom albo nie swoja strefa | ta sama zasada co przy klawiaturze |

**Powtórzony identyfikator komendy** nie jest odrzucany — „co najmniej
raz" w MQTT czyni duplikaty czymś zwyczajnym — po prostu **nie jest
wykonywany drugi raz**, a poprzednia odpowiedź zostaje opublikowana
ponownie.

## Każda odmowa to cichy alarm

Odrzucona komenda wygląda jak ktoś próbujący klamki. Podnosi alarm EPW
`REMOTE_COMMAND_REFUSED` — cichy dosłownie: nie rusza sygnalizatora,
który chodzi za naruszeniami linii, a nie za odrzuconymi wiadomościami.
Alarm jedzie przez MQTT jak każdy inny, więc to Home Assistant robi
z niego powiadomienie na telefon.

Przyjęta czy odrzucona, każda komenda trafia do dziennika audytowego
**z nazwiskiem osoby**.

## Gdzie naprawdę leży granica

Skoro Home Assistant steruje tym sterownikiem, to **bezpieczeństwo
samego HA jest granicą**. Kto go przejmie, wyśle komendy tokenem, który
tam leży. Ten kanał daje przypisanie do osoby w dzienniku, zakres per
osoba i odporność na powtórki i duplikaty. Nie chroni przed przejętym
Home Assistantem.

W praktyce: z zewnątrz łączysz się z HA (VPN albo jego własna usługa
zdalna), a nie z brokerem; broker zostaje w sieci lokalnej, z TLS
i własnym kontem; jeden token na osobę, nigdy jeden wspólny — inaczej
dziennik przestaje umieć powiedzieć, kto co zrobił.
