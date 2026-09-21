# Kreator miernika pokazuje pusta liste

OBJAW: kreator miernika (przycisk Kreator... przy elemencie Miernik) pokazuje pusta liste zamiast aparatow do wyboru.

PRZYCZYNA: kreator pokazuje WYLACZNIE aparaty o zachowaniu MEASURED ([4.6](help://synoptic/dev-measured)) - jesli w projekcie nie ma jeszcze zadnego takiego aparatu (albo istniejace maja inne zachowanie), lista jest pusta.

CO ZROBIC: Aparaty > Lista aparatow... > + Dodaj, ustaw Zachowanie na MEASURED, wypelnij i zapisz. Miernik trzeba zamknac i otworzyc kreator ponownie, zeby zobaczyc nowo dodany aparat.
