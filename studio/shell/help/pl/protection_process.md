# Zabezpieczenia procesowe

Progi na punktach analogowych, oceniane **w sterowniku**, na żywo.
Temperatura kotła, ciśnienie, poziom w zbiorniku.

Po lewej lista zabezpieczeń, po prawej konfiguracja zaznaczonego.

| Pole | Znaczenie |
|---|---|
| **Id / Nazwa** | identyfikator i czytelna nazwa |
| **Punkt** | punkt **analogowy (AI)** — inny rodzaj zgłosi [Sprawdź projekt](help://validation) |
| **Próg górny** | powyżej tego zabezpieczenie jest przekroczone |
| **Próg dolny** | poniżej tego również |
| **Histereza** | o ile wartość musi wrócić, żeby przestało być przekroczone |
| **Zwłoka (s)** | jak długo musi trwać przekroczenie, zanim zabezpieczenie zadziała |
| **En.** | czy zabezpieczenie jest włączone |

Progi są w **jednostkach inżynierskich** punktu — tych z [rejestru
punktów](help://points), nie w surowych wartościach z karty.

## Co się dzieje w sterowniku

Zabezpieczenie wystawia tag `Process.<id>.Exceeded`. Co ma się wtedy
stać — zamknięcie zaworu, zatrzymanie pompy, alarm — jest **linią
[logiki](help://logic)**, nie ustawieniem tutaj.

Histereza i zwłoka są po to, żeby drgająca wartość na granicy progu nie
przerzucała zabezpieczenia w kółko.

## Weryfikacja

**[Test zabezpieczeń](help://protection_tests)** potrafi to sprawdzić
bez rozbierania instalacji: wymusza wartość ponad próg, mierzy czas
zadziałania i porównuje go ze zwłoką, a potem wraca w zakres i mierzy
czas skasowania.
