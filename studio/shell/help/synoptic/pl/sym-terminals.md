# 6.2 Zaciski zawsze na srodku krawedzi

Kazdy zacisk symbolu lezy ZAWSZE dokladnie na srodku jednej z czterech krawedzi (gora, dol, lewo, prawo) obiektu - rejestr symbolu deklaruje TYLKO, ktora to krawedz, nigdy surowej pozycji x/y. Faktyczna pozycja jest wyliczana z aktualnej szerokosci i wysokosci obiektu (`getObjectTerminals` w `Terminals.ts`) w momencie, gdy jest potrzebna, nie zapisana na stale.

Konsekwencja praktyczna: gdy symbol jest zmieniony rozmiarem (np. zawor rozciagniety, zeby wpasowac sie w istniejacy uklad rury), jego zacisk PODAZA za nowym srodkiem krawedzi automatycznie - nie zostaje przypiety do miejsca, w ktorym byl przy domyslnym rozmiarze. Wyjatkiem jest punkt graniczny ([5.7](help://synoptic/sch-boundary-point)), ktorego jedyny zacisk zalezy od pola Boundary Port Side, a nie od rozmiaru.
