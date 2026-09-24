"""Unabhängige Referenzen für die Tests: eigenes Kruskal (Ordnung (Kosten, Nummer)), Zufallsgraphen mit Gleichständen, Pfadsuche, Zusammenhang."""


def find(p, x):
    while p[x] != x:
        p[x] = p[p[x]]
        x = p[x]
    return x


def ref_mst(n, edges):
    """Spannwald als Menge von Kantennummern; `edges` = dict Nummer -> (u, v, w) oder Sequenz (u, v, w)."""
    items = edges.items() if isinstance(edges, dict) else enumerate(edges)
    p = list(range(n))
    out = set()
    for i, (u, v, w) in sorted(items, key=lambda t: (t[1][2], t[0])):
        a, b = find(p, u), find(p, v)
        if a != b:
            p[a] = b
            out.add(i)
    return out


def connected(n, edges):
    p = list(range(n))
    for u, v, _w in (edges.values() if isinstance(edges, dict) else edges):
        p[find(p, u)] = find(p, v)
    return len({find(p, x) for x in range(n)}) == 1


def random_graph(rng, n=7, extra=4, wmax=6, integer=True):
    """Zusammenhängender Zufallsgraph (Zufallsbaum + `extra` weitere Kanten); ganzzahlige Kosten 1..wmax erzeugen Gleichstände."""
    pairs = set()
    for v in range(1, n):
        pairs.add((int(rng.integers(0, v)), v))
    for _ in range(extra):
        u, v = sorted(int(x) for x in rng.choice(n, size=2, replace=False))
        pairs.add((u, v))
    return [(u, v, float(rng.integers(1, wmax + 1)) if integer else float(rng.uniform(0.5, wmax))) for u, v in sorted(pairs)]


def brute_path_edges(n, edges, tree, a, b):
    """Kanten des Baumpfads a -> b (Suche über alle Baumkanten, unabhängig von der Implementierung)."""
    tree = set(tree)
    adj = {x: [] for x in range(n)}
    for i in tree:
        u, v, _w = edges[i]
        adj[u].append((v, i))
        adj[v].append((u, i))

    def dfs(x, target, seen):
        if x == target:
            return []
        seen.add(x)
        for y, i in adj[x]:
            if y not in seen:
                r = dfs(y, target, seen)
                if r is not None:
                    return [i] + r
        return None

    return dfs(a, b, set())
