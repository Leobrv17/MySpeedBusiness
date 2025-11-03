from __future__ import annotations
import random
from collections import defaultdict
from typing import List, Dict, Set, Tuple

class Planner:
    """
    Planificateur avec chefs fixes (fournis séparément), rotatifs et contraintes:
      - T tables = nb de chefs (chefs immobiles, non passés dans le plan renvoyé)
      - rot_per_table = k-1 (k ∈ [5..10] inclut le chef)
      - S sessions
    Contraintes:
      * un rotatif ne revient jamais à la même table (=> ne revoit pas le même chef)
      * aucune paire de rotatifs ne se retrouve ensemble plus d'une fois
      * byes autorisés si tout ne rentre pas
    Retour:
      plan[s][t] = [rotator_id, ...] (sans les chefs)
    """

    def build_plan(
        self,
        *,
        leads: List[int],          # IDs chefs (pour info, non utilisés directement)
        rotators: List[int],       # IDs rotatifs
        sessions: int,             # S
        rot_per_table: int,        # k - 1
        seed: int | None = None,
    ) -> List[List[List[int]]]:
        rng = random.Random(seed)
        T = len(leads)
        S = sessions
        if T <= 0 or S <= 0 or rot_per_table <= 0:
            return []

        # historique des paires de rotatifs (pour éviter doublons)
        met_pairs: Dict[Tuple[int, int], int] = defaultdict(int)
        # historique des tables visitées par chaque rotatif
        seen_table: Dict[int, Set[int]] = defaultdict(set)

        plan: List[List[List[int]]] = []
        pool = rotators[:]
        rng.shuffle(pool)

        for s in range(S):
            tables: List[List[int]] = [[] for _ in range(T)]
            order = pool[:]
            rng.shuffle(order)

            # Assignation gloutonne avec contraintes
            for p in order:
                # tables autorisées: non encore visitées, non pleines
                candidates = [t for t in range(T) if t not in seen_table[p] and len(tables[t]) < rot_per_table]
                if not candidates:
                    # bye si rien de valable
                    continue

                # score = nb de paires déjà vues si on place p à la table t
                best_t, best_score = None, 10**9
                for t in candidates:
                    score = 0
                    for other in tables[t]:
                        a, b = sorted((p, other))
                        score += met_pairs[(a, b)]
                    if score < best_score:
                        best_score, best_t = score, t

                if best_t is None:
                    continue

                tables[best_t].append(p)
                seen_table[p].add(best_t)

            # petite amélioration locale (réduire conflits restants)
            for _ in range(200):
                # trouve la table la plus conflictuelle
                worst_t, worst_conf = None, 0
                for t in range(T):
                    conf = 0
                    ppl = tables[t]
                    for i in range(len(ppl)):
                        for j in range(i + 1, len(ppl)):
                            a, b = sorted((ppl[i], ppl[j]))
                            conf += met_pairs[(a, b)]
                    if conf > worst_conf:
                        worst_conf, worst_t = conf, t
                if worst_conf == 0 or worst_t is None:
                    break

                improved = False
                # essaie de déplacer un membre de worst_t vers une autre table admissible
                for a in list(tables[worst_t]):
                    for t2 in range(T):
                        if t2 == worst_t:
                            continue
                        if t2 in seen_table[a]:
                            continue
                        if len(tables[t2]) >= rot_per_table:
                            continue
                        # coût si on met a à t2
                        new_conf = 0
                        for other in tables[t2]:
                            x, y = sorted((a, other))
                            new_conf += met_pairs[(x, y)]
                        if new_conf < worst_conf:
                            tables[worst_t].remove(a)
                            tables[t2].append(a)
                            seen_table[a].add(t2)
                            improved = True
                            break
                    if improved:
                        break
                if not improved:
                    break

            # mise à jour des paires rencontrées
            for t in range(T):
                ppl = tables[t]
                for i in range(len(ppl)):
                    for j in range(i + 1, len(ppl)):
                        a, b = sorted((ppl[i], ppl[j]))
                        met_pairs[(a, b)] += 1

            plan.append(tables)

        return plan
