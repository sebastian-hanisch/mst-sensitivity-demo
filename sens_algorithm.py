"""Sensitivität und Dynamik des billigsten Spannbaums (MST).

Alle Kanten haben feste Nummern; die Ordnung ist (Kosten, Nummer) - damit ist der MST auch bei Gleichständen eindeutig und "Baum ändert sich" eindeutig prüfbar.

**Toleranz** (Sensitivität): Baumkante e wird teurer, bis eine Ersatzkante einspringt: obere Toleranz = Kosten der billigsten Kante über den Schnitt, den e im Baum aufspannt, minus c_e (`bound` = diese Kosten;
keine Ersatzkante = **Brücke**, Toleranz unendlich). Nichtbaumkante f wird billiger, bis sie in den Baum wechselt: untere Toleranz = c_f minus die Kosten der teuersten Baumkante auf dem Baumpfad zwischen ihren
Enden. Eine Baumkante, die billiger, und eine Nichtbaumkante, die teurer wird, ändern den Baum nie. `tolerances_naive` (Schnitt-Suche je Baumkante, Pfadsuche je Nichtbaumkante) und `tolerances_fast`
(Tarjan-Idee: Nichtbaumkanten aufsteigend, Union-Find kontrahiert die Baumpfade; Pfadmaximum über den Kruskal-Rekonstruktionsbaum) liefern dasselbe; beide zählen Elementarschritte.

**Ausfall** (`failure`): eine Baumkante fällt aus, die billigste Kante über den Schnitt springt ein (Kostenanstieg) - oder es gibt keine (Brücke, der Baum zerfällt).

**Dynamik** (`DynamicMST`): Kante einfügen (Kreisregel: die teuerste Kante auf dem Baumpfad fliegt, falls teurer als die neue), Kante löschen (Baumkante: Ersatzkante über den Schnitt suchen), Kosten ändern
(Baumkante teurer / Nichtbaumkante billiger = möglicher Tausch, sonst nur die Kosten). `recompute` ist Kruskal von vorn (Sortieren, Union-Find) mit Schritten. Alle Schritte sind Elementarschritte (durchsuchte
Nachbareinträge, gescannte Kanten, Sortier-Vergleiche, Union-Find-Zeiger) - ein Näherungsmaß, keine Laufzeit."""

import math
from dataclasses import dataclass, field
from functools import cmp_to_key

from sens_unionfind import UnionFind

INF = math.inf


def _key(edges, i):
    return (edges[i][2], i)


# --- Kruskal von vorn -----------------------------------------------------------------------------------------------------------------------------


@dataclass
class KruskalRun:
    tree: list                                     # Kantennummern in Annahmereihenfolge
    cost: float
    steps: int                                     # Sortier-Vergleiche + Union-Find (Aufrufe + Zeigerschritte)
    comparisons: int
    order: list                                    # alle Kantennummern in Ordnung (Kosten, Nummer)
    connected: bool


def kruskal(n, items):
    """`items` = Liste (Nummer, u, v, w). Kruskal mit der Ordnung (Kosten, Nummer); gibt einen Spannwald zurück, wenn der Graph nicht zusammenhängt."""
    cnt = [0]

    def cmp(a, b):
        cnt[0] += 1
        ka, kb = (a[3], a[0]), (b[3], b[0])
        return -1 if ka < kb else (1 if ka > kb else 0)

    order = sorted(items, key=cmp_to_key(cmp))
    uf = UnionFind(n, "full")
    tree, cost = [], 0.0
    for i, u, v, w in order:
        if uf.union(u, v):
            tree.append(i)
            cost += w
    return KruskalRun(tree, cost, cnt[0] + uf.finds + uf.find_steps, cnt[0], [x[0] for x in order], uf.components == 1)


def presorted_steps(n, items_sorted):
    """Schritte (Union-Find-Aufrufe + Zeigerschritte) eines Kruskal-Durchlaufs über schon sortierte Kanten (Stopp nach n - 1 angenommenen): die stärkere Vergleichsgröße "Neuberechnung mit gehaltener
    Sortierung" ohne die Sortier-Vergleiche."""
    uf = UnionFind(n, "full")
    taken = 0
    for _i, u, v, _w in items_sorted:
        if uf.union(u, v):
            taken += 1
            if taken == n - 1:
                break
    return uf.finds + uf.find_steps


def mst(n, edges):
    """Kruskal auf einer Kantenfolge (u, v, w) mit den Nummern 0..m-1."""
    return kruskal(n, [(i, u, v, w) for i, (u, v, w) in enumerate(edges)])


def tree_adjacency(n, edges, tree):
    adj = [[] for _ in range(n)]
    for i in tree:
        u, v, _w = edges[i]
        adj[u].append((v, i))
        adj[v].append((u, i))
    return adj


def _side(adj, start, banned):
    """Knoten, die von `start` aus ohne die Kante `banned` im Baum erreichbar sind; Schritte = untersuchte Nachbareinträge."""
    seen = {start}
    stack = [start]
    steps = 0
    while stack:
        x = stack.pop()
        for y, i in adj[x]:
            if i == banned:
                continue
            steps += 1
            if y not in seen:
                seen.add(y)
                stack.append(y)
    return seen, steps


def _path(adj, u, v):
    """Kantennummern des Baumpfads u -> v (None, wenn nicht verbunden); Schritte = untersuchte Nachbareinträge."""
    parent = {u: None}
    stack = [u]
    steps = 0
    while stack:
        x = stack.pop()
        if x == v:
            break
        for y, i in adj[x]:
            steps += 1
            if y not in parent:
                parent[y] = (x, i)
                stack.append(y)
    if v not in parent:
        return None, steps
    out = []
    x = v
    while parent[x] is not None:
        x, i = parent[x]
        out.append(i)
    return out, steps


# --- Toleranzen -----------------------------------------------------------------------------------------------------------------------------------


@dataclass
class Tolerances:
    rep: dict                                      # Baumkante -> Nummer der billigsten Ersatzkante (None: Brücke)
    pmax: dict                                     # Nichtbaumkante -> Nummer der teuersten Baumkante auf dem Baumpfad
    steps: int
    sort_steps: int = 0


def tolerances_naive(n, edges, tree):
    tree = set(tree)
    nontree = [i for i in range(len(edges)) if i not in tree]
    adj = tree_adjacency(n, edges, tree)
    rep, pmax, steps = {}, {}, 0
    for e in sorted(tree):
        u = edges[e][0]
        side, s = _side(adj, u, e)
        steps += s
        best = None
        for f in nontree:
            steps += 1
            a, b, _w = edges[f]
            if (a in side) != (b in side) and (best is None or _key(edges, f) < _key(edges, best)):
                best = f
        rep[e] = best
    for f in nontree:
        a, b, _w = edges[f]
        path, s = _path(adj, a, b)
        steps += s
        pmax[f] = max(path, key=lambda i: _key(edges, i))
    return Tolerances(rep, pmax, steps)


def tolerances_fast(n, edges, tree, order=None):
    """Tarjan-Idee: (1) Kruskal-Rekonstruktionsbaum über die Baumkanten (Pfadmaximum je Nichtbaumkante durch Hochklettern bis zum gemeinsamen Vorfahren), (2) Nichtbaumkanten in aufsteigender Ordnung:
    jede belegt die noch unbedeckten Baumkanten ihres Baumpfads als Ersatz; ein Union-Find kontrahiert bedeckte Kanten. `order` = alle Kantennummern in Ordnung (aus dem Kruskal-Lauf); ohne sortiert die
    Funktion selbst und weist die Vergleiche in `sort_steps` aus."""
    tree = set(tree)
    m = len(edges)
    sort_steps = 0
    if order is None:
        cnt = [0]

        def cmp(a, b):
            cnt[0] += 1
            ka, kb = _key(edges, a), _key(edges, b)
            return -1 if ka < kb else (1 if ka > kb else 0)

        order = sorted(range(m), key=cmp_to_key(cmp))
        sort_steps = cnt[0]
    steps = 0
    # (1) Rekonstruktionsbaum
    comp = list(range(n))                                            # Union-Find mit Pfadhalbierung; die Wurzel ist zugleich Wurzel im Rekonstruktionsbaum

    def cfind(x):
        nonlocal steps
        while comp[x] != x:
            comp[x] = comp[comp[x]]
            x = comp[x]
            steps += 1
        steps += 1
        return x

    kpar = [None] * n
    klab = [None] * n
    kedge = [None] * n
    for i in order:
        if i not in tree:
            continue
        u, v, _w = edges[i]
        ra, rb = cfind(u), cfind(v)
        comp[ra] = rb
        kpar[ra], klab[ra], kedge[ra] = rb, _key(edges, i), i
    pmax = {}
    for f in order:
        if f in tree:
            continue
        x, y = edges[f][0], edges[f][1]
        last = None
        while x != y:
            steps += 1
            if kpar[x] is None and kpar[y] is None:
                raise ValueError("Graph nicht zusammenhängend")
            lx = klab[x] if klab[x] is not None else (INF, INF)
            ly = klab[y] if klab[y] is not None else (INF, INF)
            if lx < ly:
                last = kedge[x]
                x = kpar[x]
            else:
                last = kedge[y]
                y = kpar[y]
        pmax[f] = last
    # (2) Ersatzkanten: Baum wurzeln
    adj = tree_adjacency(n, edges, tree)
    parent, pedge, depth = [None] * n, [None] * n, [0] * n
    seen = [False] * n
    for r in range(n):
        if seen[r]:
            continue
        seen[r] = True
        stack = [r]
        while stack:
            x = stack.pop()
            for y, i in adj[x]:
                steps += 1
                if not seen[y]:
                    seen[y] = True
                    parent[y], pedge[y], depth[y] = x, i, depth[x] + 1
                    stack.append(y)
    cov = list(range(n))

    def vfind(x):
        nonlocal steps
        while cov[x] != x:
            cov[x] = cov[cov[x]]
            x = cov[x]
            steps += 1
        steps += 1
        return x

    rep = {e: None for e in tree}
    for f in order:
        if f in tree:
            continue
        x, y = vfind(edges[f][0]), vfind(edges[f][1])
        while x != y:
            steps += 1
            if depth[x] < depth[y]:
                x, y = y, x
            rep[pedge[x]] = f
            cov[x] = parent[x]
            x = vfind(x)
    return Tolerances(rep, pmax, steps, sort_steps)


@dataclass
class Tol:
    edge: int
    tree: bool
    cost: float
    bound: float                                   # Kosten, bei denen der Baum wechselt (None: Brücke)
    margin: float                                  # absolute Toleranz (INF bei Brücke)
    rel: float                                     # Toleranz in Prozent der Kantenkosten (INF bei Brücke)
    other: object                                  # Ersatzkante (Baumkante) bzw. teuerste Baumkante auf dem Pfad (Nichtbaumkante); None bei Brücke
    bridge: bool = False


def tolerance_table(edges, tol):
    """Je Kante eine `Tol`; Reihenfolge = Kantennummer."""
    out = []
    for i, (u, v, w) in enumerate(edges):
        if i in tol.rep:
            r = tol.rep[i]
            if r is None:
                out.append(Tol(i, True, w, None, INF, INF, None, True))
            else:
                b = edges[r][2]
                out.append(Tol(i, True, w, b, b - w, 100.0 * (b - w) / w if w > 0 else INF, r))
        else:
            g = tol.pmax[i]
            b = edges[g][2]
            out.append(Tol(i, False, w, b, w - b, 100.0 * (w - b) / w if w > 0 else INF, g))
    return out


def exceeds(edges, tol, i, new_w):
    """Sprengt die Kostenänderung der Kante i auf `new_w` (bei sonst festen Kosten) ihre Toleranz, d. h. ändert sie den Baum? Ordnung (Kosten, Nummer)."""
    t = tol[i]
    if t.bridge:
        return False
    if t.tree:
        return (new_w, i) > (t.bound, t.other)
    return (new_w, i) < (t.bound, t.other)


# --- Ausfall --------------------------------------------------------------------------------------------------------------------------------------


@dataclass
class Failure:
    edge: int
    side: set                                      # Knoten auf der Seite des ersten Endpunkts nach dem Ausfall
    rep: object                                    # einspringende Ersatzkante (None: Brücke)
    new_tree: list
    delta: float                                   # Kostenanstieg (INF bei Brücke)
    rel: float                                     # Kostenanstieg in Prozent der Baumkosten (INF bei Brücke)
    steps: int


def failure(n, edges, tree, e):
    tree = set(tree)
    if e not in tree:
        raise ValueError("keine Baumkante")
    adj = tree_adjacency(n, edges, tree)
    side, steps = _side(adj, edges[e][0], e)
    best = None
    for f in range(len(edges)):
        if f in tree:
            continue
        steps += 1
        a, b, _w = edges[f]
        if (a in side) != (b in side) and (best is None or _key(edges, f) < _key(edges, best)):
            best = f
    base = sum(edges[i][2] for i in tree)
    new_tree = sorted(tree - {e} | ({best} if best is not None else set()))
    if best is None:
        return Failure(e, side, None, new_tree, INF, INF, steps)
    delta = edges[best][2] - edges[e][2]
    return Failure(e, side, best, new_tree, delta, 100.0 * delta / base if base > 0 else 0.0, steps)


def failure_table(n, edges, tree):
    """Alle Baumkanten-Ausfälle, kritischste zuerst (Brücken, dann absteigender Kostenanstieg)."""
    fs = [failure(n, edges, tree, e) for e in sorted(tree)]
    return sorted(fs, key=lambda f: (f.rep is not None, -f.delta if f.rep is not None else 0.0, f.edge))


# --- Dynamischer MST ------------------------------------------------------------------------------------------------------------------------------


@dataclass
class Op:
    kind: str                                      # "insert" | "delete" | "cost"
    edge: int
    steps: int
    changed: bool                                  # die Kantenmenge des Baums hat sich geändert
    swapped_out: object = None                     # aus dem Baum entfernte Kante (Tausch)
    swapped_in: object = None                      # neu in den Baum genommene Kante
    detail: dict = field(default_factory=dict)


class DynamicMST:
    """Hält einen Spannwald des billigsten Baums unter Einfügen, Löschen und Kostenänderungen; Nummern bleiben fest, neue Kanten bekommen die nächste Nummer."""

    def __init__(self, n, edges):
        self.n = n
        self.ends = {}
        self.w = {}
        self.tree = set()
        self.adj = [dict() for _ in range(n)]
        self.next_id = 0
        for u, v, w in edges:
            self.ends[self.next_id] = (u, v)
            self.w[self.next_id] = float(w)
            self.next_id += 1
        for i in kruskal(n, [(i, self.ends[i][0], self.ends[i][1], self.w[i]) for i in self.ends]).tree:
            self._link(i)

    # -- Hilfen
    def key(self, i):
        return (self.w[i], i)

    def cost(self):
        return math.fsum(self.w[i] for i in self.tree)

    def alive(self):
        return sorted(self.ends)

    def items(self):
        return [(i, self.ends[i][0], self.ends[i][1], self.w[i]) for i in sorted(self.ends)]

    def _link(self, i):
        u, v = self.ends[i]
        self.tree.add(i)
        self.adj[u][v] = i
        self.adj[v][u] = i

    def _unlink(self, i):
        u, v = self.ends[i]
        self.tree.discard(i)
        del self.adj[u][v]
        del self.adj[v][u]

    def _path(self, u, v):
        return _path(self._adjlist_lazy(), u, v)

    def _adjlist_lazy(self):
        return _DictAdj(self.adj)

    def _replacement(self, e):
        """Billigste Nichtbaumkante über den Schnitt der (schon entfernten) Baumkante e. Gibt (Kante, Schritte)."""
        u, v = self.ends[e]
        adj = self._adjlist_lazy()
        side, steps = _side(adj, u, None)
        best = None
        for f in self.ends:
            if f in self.tree or f == e:
                continue
            steps += 1
            a, b = self.ends[f]
            if (a in side) != (b in side) and (best is None or self.key(f) < self.key(best)):
                best = f
        return best, steps

    # -- Operationen
    def insert(self, u, v, w):
        i = self.next_id
        self.next_id += 1
        self.ends[i] = (min(u, v), max(u, v))
        self.w[i] = float(w)
        path, steps = self._path(u, v)
        steps += 1
        if path is None:
            self._link(i)
            return Op("insert", i, steps, True, None, i)
        g = max(path, key=self.key)
        if self.key(i) < self.key(g):
            self._unlink(g)
            self._link(i)
            return Op("insert", i, steps, True, g, i)
        return Op("insert", i, steps, False)

    def delete(self, e):
        if e not in self.ends:
            raise KeyError(e)
        if e not in self.tree:
            del self.ends[e], self.w[e]
            return Op("delete", e, 1, False)
        self._unlink(e)
        f, steps = self._replacement(e)
        if f is not None:
            self._link(f)
        del self.ends[e], self.w[e]
        return Op("delete", e, max(1, steps), True, e, f)

    def set_cost(self, e, w):
        old = self.w[e]
        w = float(w)
        if e in self.tree:
            if w <= old:
                self.w[e] = w
                return Op("cost", e, 1, False)
            self._unlink(e)
            self.w[e] = w
            f, steps = self._replacement(e)
            if f is not None and self.key(f) < self.key(e):
                self._link(f)
                return Op("cost", e, max(1, steps), True, e, f)
            self._link(e)
            return Op("cost", e, max(1, steps), False)
        if w >= old:
            self.w[e] = w
            return Op("cost", e, 1, False)
        self.w[e] = w
        u, v = self.ends[e]
        path, steps = self._path(u, v)
        g = max(path, key=self.key)
        if self.key(e) < self.key(g):
            self._unlink(g)
            self._link(e)
            return Op("cost", e, max(1, steps), True, g, e)
        return Op("cost", e, max(1, steps), False)


class _DictAdj:
    """Sicht auf die Nachbar-Dictionaries als Nachbarlisten (für `_side`/`_path`)."""

    def __init__(self, adj):
        self.adj = adj

    def __getitem__(self, x):
        return [(y, i) for y, i in self.adj[x].items()]
