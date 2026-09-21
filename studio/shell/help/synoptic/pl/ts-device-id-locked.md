# Id aparatu nie da sie zmienic

OBJAW: przy edycji istniejacego aparatu pole Id jest zaszarzone i nie da sie go zmienic.

PRZYCZYNA: id jest niezmienny CELOWO - to klucz, po ktorym symbole na ekranie i wiersze mierzenikow/paneli odwoluja sie do aparatu ([4.2](help://synoptic/dev-naming)). Edycja go na zywo popsulaby kazde takie odwolanie.

CO ZROBIC: utworz nowy aparat z zadanym identyfikatorem, recznie przepisz do niego wartosci pol ze starego (Duplikuj czysci tylko id/oznaczenie, wiec moze pomoc jako punkt startowy), a potem usun stary aparat. Kazdy symbol wskazujacy na stary identyfikator trzeba bedzie recznie przepiac na nowy - usuniecie aparatu nie ostrzega, ile symboli na ekranie na niego wskazuje.
