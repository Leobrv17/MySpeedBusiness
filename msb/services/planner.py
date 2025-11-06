from __future__ import annotations
import random
from collections import defaultdict
from typing import List, Dict, Set, Tuple

class Planner:
    """
    Génère un plan tel que:
      - tout le monde a une place à chaque session (pas de bye)
      - capacités exactes par table (k_t, 5..10)
      - chefs fixes facultatifs: fixed_leads[t] occupe 1 place à la table t (toute session)
      - priorité:
          * "coverage"   : maximiser nouvelles rencontres (éviter les répétitions)
          * "exclusivity": interdire les répétitions (si impossible, les minimiser)
    Entrées:
      - num_tables: T
      - sessions: S
      - table_capacities: List[int] de longueur T, somme = N (= nb total de personnes)
      - fixed_leads: List[int] (0..T), position implicite: lead i -> table i
      - people: List[int] (toutes les autres personnes à placer)
    Sortie:
      plan[s][t] = [pids...] longueur == k_t (chef d'abord s'il y en a un)
    """
    def build_plan(
        self,
        *,
        num_tables: int,
        sessions: int,
        table_capacities: List[int],
        fixed_leads: List[int],
        priority: str,        # "coverage" | "exclusivity"
        people: List[int],
        seed: int | None = None,
    ) -> List[List[List[int]]]:
        rng = random.Random(seed)
        T = num_tables
        S = sessions
        caps = list(table_capacities)
        leads = list(fixed_leads)
        assert len(caps) == T, "table_capacities doit avoir T éléments"
        if len(leads) > T:
            leads = leads[:T]

        # rotatif à placer = people (toutes les personnes hors chefs)
        # nb total = somme caps
        N = sum(caps)
        total_fixed = len(leads)
        if total_fixed > 0:
            # retire les chefs du pool s'ils y sont
            people = [p for p in people if p not in set(leads)]

        # capacité rotateurs par table = k_t - (1 si chef sinon 0)
        rot_need = [caps[t] - (1 if t < len(leads) else 0) for t in range(T)]
        if any(k < 0 for k in rot_need):
            raise ValueError("Capacité négative: trop de chefs par rapport aux capacités.")
        if sum(rot_need) != len(people):
            # si déséquilibre (chefs partiels), on rééquilibre en ajoutant des "leads virtuels" (=0 place prise)
            diff = sum(rot_need) - len(people)
            if diff != 0:
                # Stratégie simple: si on manque de personnes, on réduit des places sur les plus grosses tables
                # (mais en pratique, avec caps = somme N, ça ne devrait pas arriver)
                adj = diff
                for t in sorted(range(T), key=lambda i: rot_need[i], reverse=True):
                    if adj == 0: break
                    take = min(adj, max(0, rot_need[t]-1))
                    rot_need[t] -= take
                    adj -= take
                if sum(rot_need) != len(people):
                    raise ValueError("Incohérence capacités vs personnes.")

        # états pour éviter les répétitions
        met_pairs: Dict[Tuple[int, int], int] = defaultdict(int)
        seen_with_lead: Dict[int, Set[int]] = defaultdict(set)  # personne -> set(index table) si chef fixe
        seen_table: Dict[int, Set[int]] = defaultdict(set)      # personne -> set(index table), pour limiter re-table

        plan: List[List[List[int]]] = []

        # shuffle initial global
        pool = people[:]
        rng.shuffle(pool)

        # pré-calcul: tables indexées 0..T-1 ; leads[t] si t < len(leads)
        for s in range(S):
            # on prépare les tables de la session avec chef en tête si présent
            tables: List[List[int]] = []
            for t in range(T):
                row = []
                if t < len(leads):
                    row.append(leads[t])
                tables.append(row)

            # tailles cibles rotatifs pour cette session
            need = rot_need[:]  # constants

            # ordre d'assignation
            order = pool[:]
            rng.shuffle(order)

            # glouton: placer chacun en minimisant le coût (répétitions)
            for p in order:
                # build candidates: tables non pleines et (optionnel) non revisitées trop souvent
                candidates = []
                for t in range(T):
                    # place dispo ?
                    cap = caps[t]
                    if len(tables[t]) >= cap:  # pleine
                        continue
                    # si chef fixe à t, on peut éviter qu'une personne revienne trop souvent au même chef
                    if t in seen_table[p]:
                        # on pénalise mais on n'interdit pas pour garantir remplissage
                        pass
                    candidates.append(t)

                if not candidates:
                    # toutes pleines -> devrait pas arriver car somme caps == N
                    continue

                # score:
                #  - exclusivity: très forte pénalité si paire déjà vue
                #  - coverage: pénalité légère si paire déjà vue, bonus si nouvelle table
                best_t, best_score = None, 10**9
                for t in candidates:
                    score = 0
                    # pénalise re-table
                    if t in seen_table[p]:
                        score += 3 if priority == "exclusivity" else 1
                    # pénalise pairs déjà rencontrées
                    for other in tables[t]:
                        a, b = sorted((p, other))
                        if met_pairs[(a, b)] > 0:
                            score += 100 if priority == "exclusivity" else 5
                    if score < best_score:
                        best_score, best_t = score, t

                tables[best_t].append(p)
                seen_table[p].add(best_t)
                if best_t < len(leads):
                    seen_with_lead[p].add(best_t)

            # une fois remplie, on met à jour les paires rencontrées
            for t in range(T):
                ppl = tables[t]
                for i in range(len(ppl)):
                    for j in range(i + 1, len(ppl)):
                        a, b = sorted((ppl[i], ppl[j]))
                        met_pairs[(a, b)] += 1

            plan.append(tables)

        return plan
