import random
from collections import deque

# ---------- Moves (18 total) ----------
FACES = ["U", "R", "F", "D", "L", "B"]
MOVES = [f + s for f in FACES for s in ["", "'", "2"]]

def _stickers():
    r = (-1, 0, 1)
    rv = (1, 0, -1)
    s = []
    for z in r:
        for x in r:
            s.append(((x, 1, z), (0, 1, 0)))       # U
    for y in rv:
        for z in rv:
            s.append(((1, y, z), (1, 0, 0)))       # R
    for y in rv:
        for x in r:
            s.append(((x, y, 1), (0, 0, 1)))       # F
    for z in rv:
        for x in r:
            s.append(((x, -1, z), (0, -1, 0)))     # D
    for y in rv:
        for z in r:
            s.append(((-1, y, z), (-1, 0, 0)))     # L
    for y in rv:
        for x in rv:
            s.append(((x, y, -1), (0, 0, -1)))     # B
    return s


_ST = _stickers()
_IDX = {st: i for i, st in enumerate(_ST)}


def _rot90(v, axis):
    x, y, z = v
    if axis == 0:
        return (x, -z, y)
    if axis == 1:
        return (z, y, -x)
    return (-y, x, z)


def _rot(v, axis, k):
    for _ in range(k % 4):
        v = _rot90(v, axis)
    return v


_INFO = {
    "U": (1, 1, -1), "R": (0, 1, -1), "F": (2, 1, -1),
    "D": (1, -1, 1), "L": (0, -1, 1), "B": (2, -1, 1),
}


def _perm(move):
    face, suf = move[0], move[1:]
    axis, sign, k = _INFO[face]
    turns = {"": k, "'": -k, "2": 2 * k}[suf]
    src = list(range(54))
    for i, (pos, nrm) in enumerate(_ST):
        if pos[axis] == sign:
            j = _IDX[(_rot(pos, axis, turns), _rot(nrm, axis, turns))]
            src[j] = i
    return src


_PERMS = {m: _perm(m) for m in MOVES}

SOLVED = "".join(f * 9 for f in "URFDLB")


def new_cube():
    return SOLVED


def apply_move(state, move):
    p = _PERMS[move]
    return "".join(state[i] for i in p)


def facelets(state):
    return state


def is_solved(state):
    return state == SOLVED


def random_scramble(n):
    while True:
        seq, last, state = [], None, SOLVED
        for _ in range(n):
            f = random.choice([x for x in FACES if x != last])
            m = f + random.choice(["", "'", "2"])
            seq.append(m)
            state = apply_move(state, m)
            last = f
        if not is_solved(state):
            return seq, state


# ---------- BFS (exact shortest, distance <= 5) ----------
def _bfs(start, depth):
    seen = {start: 0}
    q = deque([(start, 0)])
    while q:
        s, d = q.popleft()
        if d == depth:
            continue
        for m in MOVES:
            n = apply_move(s, m)
            if n not in seen:
                seen[n] = d + 1
                q.append((n, d + 1))
    return seen


_TABLE = None


def shortest_distance(state):
    global _TABLE
    if _TABLE is None:
        _TABLE = _bfs(SOLVED, 3)
    seen = _bfs(state, 2)
    best = None
    for k, d1 in seen.items():
        if k in _TABLE:
            total = d1 + _TABLE[k]
            if best is None or total < best:
                best = total
    return best


if __name__ == "__main__":
    
    s = SOLVED
    for _ in range(6):
        for m in ["R", "U", "R'", "U'"]:
            s = apply_move(s, m)
    print("Self-test :", is_solved(s))

    seq, cube = random_scramble(4)
    print("Scramble:", seq)
    print("State   :", facelets(cube))
    print("Solved? :", is_solved(cube))
    print("Shortest:", shortest_distance(cube))