# 5.6 Walidacja sieci: niezgodnosc osrodkow, przewod donikad

Walidacja sieci dziala na juz wyliczonych sieciach (`validateNets` w `NetResolver.ts`), nie na pojedynczych przewodach:

| Kod | Waga | Znaczenie |
| --- | --- | --- |
| MIXED_MEDIUM | blad | Siec dotyka zaciskow z wiecej niz jednego osrodka - patrz [5.3](help://synoptic/sch-media). |
| DANGLING_NET | ostrzezenie | Przewod nie dotyka zadnego zacisku - "przewod donikad". |
| MULTIPLE_SOURCES | ostrzezenie | Dwa lub wiecej punkty graniczne SOURCE spiete w jedna siec - dwa zasilania razem. |

To rozne od walidacji ksztaltu pojedynczego przewodu (np. zakaz odcinka po skosie) - ta druga jest sprawdzana na poziomie schematu jako calosci przy zapisie (`validateProjectSchema` w `ProjectSchema.ts`), nie na poziomie sieci.
