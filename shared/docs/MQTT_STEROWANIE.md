# Sterowanie z Home Assistanta przez MQTT

Stan po zadaniu „komendy przez MQTT" (2026-09-20). Do tej pory łącze MQTT
było praktycznie jednokierunkowe: sterownik wystawiał stan, a jedyną
drogą do środka były mapowania „temat → tag `Link.*`", czyli dane do
pokazania, których nic w sterowniku nie wykonuje.

Teraz HAOS może **sterować**: alarmówką, nastawami i aparatami.
Wymuszenia (force) celowo zostają poza tym kanałem.

---

## 1. Jak to jest poskładane

| Warstwa | Plik | Odpowiada za |
|---|---|---|
| Transport | `runtime/epw_os/core/mqtt_manager.py` | subskrypcja tematu komend, przekazanie surowej wiadomości, publikacja odpowiedzi. **Nie wie nic** o tożsamości ani o tym, co komenda robi |
| Bramka | `runtime/epw_os/core/remote_commands.py` | czy wiadomość jest prawdziwa, kto ją wysłał, czy wolno mu — i wykonanie przez te same managery, co panel |
| Tożsamość | `runtime/epw_os/core/access_manager.py` | token zdalny per osoba (hash, plik lokalny sterownika) |

Ten podział jest celowy: `mqtt_manager.py` nadal nie importuje
`CommandManager` ani niczego, co rusza obiektem — dostaje callback i tyle.

## 2. Dlaczego tożsamość jedzie w wiadomości

**Home Assistant ma jedno konto MQTT.** Wszyscy klikają w HA, ale do
brokera idzie zawsze ten sam klient — broker nie odróżni Kowalskiego od
Nowaka. Uprawnienia na brokerze mogą powiedzieć najwyżej „HA wolno
publikować komendy". Skoro mają to być **konkretne osoby**, tożsamość
musi jechać w treści i sterownik musi ją sam sprawdzić — w oparciu o
kartotekę, którą i tak już ma (`intrusion.users` w projekcie).

**Token ≠ kod na klawiaturę.** To dwa osobne sekrety tej samej osoby.
Token leży w automatyzacji HA na innej maszynie; gdyby był tym samym
kodem, wyciek z HA otwierałby panel przy szafie. Unieważnienie tokenu
nie rusza kodu i odwrotnie.

## 3. Co dokładnie sprawdza bramka, po kolei

1. **retained → odmowa + cichy alarm.** Wiadomość „przypięta" na brokerze
   jest odtwarzana każdemu, kto się połączy — w tym sterownikowi po
   restarcie. „Rozbrój" wysłane raz jako retained rozbrajałoby obiekt po
   każdym zaniku zasilania.
2. **nie-JSON / nie-obiekt / brak `id` → odmowa + cichy alarm.**
3. **`ts` starszy niż 120 s → odmowa + cichy alarm** (przechwycona
   wiadomość jest bezużyteczna minutę później).
4. **`id` już widziane → wykonanie POMIJANE**, poprzednia odpowiedź
   publikowana ponownie. To nie jest atak: MQTT QoS 1 znaczy „co najmniej
   raz", więc duplikat bywa normalny i nie może uzbroić drugi raz.
5. **token nieznany / osoba wyłączona / token należy do kogo innego niż
   mówi pole `user` → odmowa + cichy alarm.**
6. **poziom i strefy osoby** — sprawdzane dokładnie tak, jak przy panelu,
   przez te same managery. Nic nie jest tu przepisane drugi raz.
7. Dopiero teraz **wykonanie** i publikacja wyniku.

„Cichy alarm" to alarm w EPW (`REMOTE_COMMAND_REFUSED`, priorytet 3) —
**cichy dosłownie**: to zdarzenie nie rusza sygnalizatora alarmówki
(`SSWIN.SIREN_ACTIVE` chodzi za naruszeniem linii, nie za odrzuconą
komendą), a alarmy i tak jadą przez MQTT, więc to HA robi z tego
powiadomienie na telefon. Każda komenda, przyjęta czy odrzucona,
trafia też do dziennika audytowego z **nazwiskiem**, nie z „Panel:Operator".

## 4. Tematy i format wiadomości

- komendy: `<prefiks>/cmd` (domyślny prefiks: `epw/<id sterownika>`)
- odpowiedzi: `<prefiks>/cmd/result`

```json
{
  "id": "unikalny-identyfikator-komendy",
  "ts": 1758300000,
  "user": "U1",
  "token": "<token tej osoby>",
  "action": "intrusion",
  "what": "arm_night",
  "zone": "Z1"
}
```

| `action` | `what` | pozostałe pola | poziom |
|---|---|---|---|
| `intrusion` | `arm`, `arm_night`, `disarm`, `reset` | `zone` (id strefy albo `all`), opcjonalnie `force: true` | Operator + strefa |
| `intrusion` | `silence` | — (sygnalizator jest jeden, nie per strefa) | Operator + strefa w alarmie |
| `apparatus` | `CLOSE`, `OPEN` | `target` (id aparatu) | Operator |
| `setting` | `process_protection` | `target`, `values: {upper_threshold, lower_threshold, hysteresis, delay_seconds, enabled}` | Engineer |
| `setting` | `electrical_stage` | `target` (funkcja), `stage`, `values: {enabled, setting, hysteresis, delay_ms, action}` | Engineer |

Wartości nastaw siedzą w osobnym obiekcie `values` — bo etap
zabezpieczenia ma pola `setting` i `action`, a koperta komendy też.
Czytane płasko, słowa koperty wciekały do zapisywanych wartości (złapane
przez własny test tego modułu).

Odpowiedź: `{"id", "accepted", "reason", "detail", "user"}`, a przy
duplikacie dodatkowo `"duplicate": true`.

## 5. Gdzie się to ustawia

1. **Studio → Alarmówka → Użytkownicy**: kto istnieje, jaki poziom, które
   strefy. Kodów i tokenów tu nie ma i nigdy nie będzie — `projekt.epw`
   jedzie do Studia, do gita i po sieci.
2. **Panel → Ustawienia → Użytkownicy alarmówki…** (Engineer): „Wydaj
   token zdalny". Token pokazuje się **raz**; zgubiony zastępuje się
   nowym, co natychmiast unieważnia poprzedni.
3. **Home Assistant**: token wklejasz do automatyzacji tej osoby.

## 6. Przykład automatyzacji HA

```yaml
alias: EPW - uzbrój dozór nocny
triggers:
  - trigger: state
    entity_id: input_boolean.dozor_nocny
    to: "on"
actions:
  - action: mqtt.publish
    data:
      topic: epw/EPW-01/cmd
      qos: 1
      retain: false          # KONIECZNIE false - retained jest odrzucane
      payload: >-
        {
          "id": "{{ now().timestamp() | int }}-{{ range(1000,9999) | random }}",
          "ts": {{ now().timestamp() | int }},
          "user": "U1",
          "token": "!secret epw_token_kowalski",
          "action": "intrusion",
          "what": "arm_night",
          "zone": "all"
        }
```

Odpowiedź warto sobie wystawić jako sensor, żeby widzieć, czemu komenda
nie przeszła:

```yaml
mqtt:
  sensor:
    - name: "EPW wynik komendy"
      state_topic: "epw/EPW-01/cmd/result"
      value_template: "{{ value_json.accepted }}"
      json_attributes_topic: "epw/EPW-01/cmd/result"
```

## 7. Gdzie naprawdę leży granica — przeczytaj to raz

Skoro HAOS ma sterować wszystkim, to **bezpieczeństwo HAOS-a jest
prawdziwą granicą**. Kto przejmie HAOS, wyśle komendę z tokenem, który
tam leży. Ten kanał daje: przypisanie do osoby w dzienniku, odcięcie
wszystkiego innego w sieci, zakres per osoba i odporność na powtórki.
Nie daje ochrony przed przejętym HAOS-em.

Praktycznie:

- **dostęp z zewnątrz robisz do HAOS-a** (VPN albo Nabu Casa), nie do
  brokera — port 1883 nigdy nie idzie na świat;
- **broker z TLS i własnym kontem** dla sterownika; sterownik ostrzega
  przy starcie, gdy broker nie jest lokalny;
- **jeden token na osobę**, nie jeden wspólny — inaczej dziennik znowu
  przestaje mówić, kto co zrobił.

## 7a. Wyciszenie to nie rozbrojenie

`what: "silence"` zatrzymuje **sam dźwięk**. Strefa zostaje w ALARM,
pamięć alarmu zostaje, lampa (`SSWIN.STROBE_ACTIVE`) świeci dalej. To jest
sens osobnej komendy: „wyłącz hałas" i „sprawa jest załatwiona" to dwie
różne decyzje, często podejmowane kilkanaście minut od siebie. Do tej
drugiej służy `reset`.

Sama syrena nie jest w EPW-OS żadnym wyjściem — sterownik wystawia stan
(`SSWIN.SIREN_ACTIVE`), a to, na którym DO wisi syrena, rysuje inżynier w
Logic Studio. Opis: `LOGIKA_W_RUNTIME.md`, rozdział o `SSWIN.*`.

## 8. Czego tu nie ma i dlaczego

- **Wymuszenia (force)** — narzędzie serwisanta stojącego przy szafie,
  trzymane przy życiu jego heartbeatem. Zdalnie nie ma sensu, więc nie ma
  go w tablicy akcji bramki (nie „odmawiamy tej osobie" — po prostu takiej
  komendy nie ma).
- **Zmiana składu urządzenia, kart, punktów** — to struktura z projektu,
  nie nastawa; idzie przez Studio i instalację projektu.
