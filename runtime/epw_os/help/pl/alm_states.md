# Różnica między alarmem aktywnym a niepotwierdzonym

Alarm w programie może być w czterech stanach, rozróżnianych kolorem
wiersza:

| Stan | Kolor wiersza | Znaczenie |
|---|---|---|
| Aktywny, niepotwierdzony | ciemny czerwony | przyczyna trwa, nikt jeszcze nie potwierdził |
| Aktywny, potwierdzony | ciemny bursztynowy | przyczyna trwa, ktoś już to zauważył |
| Ustąpiony, niepotwierdzony | szary | przyczyna minęła, ale nikt tego nie potwierdził |
| Normalny | biały | przyczyna minęła i alarm potwierdzono |

Najważniejsza różnica: **"aktywny" opisuje, czy przyczyna alarmu wciąż
trwa**, a **"potwierdzony" opisuje, czy ktoś już to zauważył** — to dwie
niezależne od siebie rzeczy. Alarm może więc ustąpić, zanim ktokolwiek
zdąży go potwierdzić, i pozostanie widoczny aż do kwitowania.
