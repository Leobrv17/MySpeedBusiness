from __future__ import annotations

import random
from collections import defaultdict
from typing import Dict, List, Set, Tuple


class Planner:
    """
    Génère un plan de placement en sessions en respectant en priorité
    l'absence de doublons de tables et de paires déjà rencontrées.
    """

    def build_plan(
        self,
        *,
        num_tables: int,
        sessions: int,
        table_capacities: List[int],
        fixed_leads: List[int],
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

        total_people = len(people) + len(leads)
        expected_people = sum(caps)
        if total_people != expected_people:
            raise ValueError(
                f"Somme des capacités ({expected_people}) incohérente avec le nombre de personnes fourni ({total_people})."
            )

        # Supprime les chefs éventuels du pool mobile pour éviter les doublons
        mobile_people = [p for p in people if p not in set(leads)]

        # capacité mobile par table (chef prenant une place)
        rot_need = [caps[t] - (1 if t < len(leads) else 0) for t in range(T)]
        if any(k < 0 for k in rot_need):
            raise ValueError("Capacité négative: trop de chefs par rapport aux capacités.")

        if sum(rot_need) != len(mobile_people):
            raise ValueError("Incohérence capacités vs personnes à placer.")

        # Vérifie la faisabilité théorique (information uniquement)
        max_cap = max(caps)
        feasible = S * (max_cap - 1) >= expected_people - 1

        # Suivi des rencontres et des rotations
        met_pairs: Dict[Tuple[int, int], int] = defaultdict(int)
        seen_tables: Dict[int, Set[int]] = defaultdict(set)
        meets_count: Dict[int, Set[int]] = defaultdict(set)
        sessions_played: Dict[int, int] = defaultdict(int)

        plan: List[List[List[int]]] = []

        # ordre initial pour la première session
        base_pool = mobile_people[:]
        rng.shuffle(base_pool)

        for s in range(S):
            # Tables préremplies avec les chefs
            tables: List[List[int]] = []
            for t in range(T):
                row = []
                if t < len(leads):
                    row.append(leads[t])
                tables.append(row)

            # Choix de l'ordre de placement
            if s == 0:
                order = base_pool[:]
            else:
                order = sorted(
                    mobile_people,
                    key=lambda p: (
                        len(meets_count[p]),
                        sessions_played[p],
                        len(seen_tables[p]),
                        rng.random(),
                    ),
                )

            for p in order:
                # Tables non pleines
                available_tables = [t for t in range(T) if len(tables[t]) < caps[t]]
                if not available_tables:
                    continue

                # Priorité: tables jamais visitées par p si possible
                unvisited = [t for t in available_tables if t not in seen_tables[p]]
                candidates = unvisited if unvisited else available_tables

                # Priorité: aucune paire déjà rencontrée
                safe_tables = []
                for t in candidates:
                    conflicts = sum(1 for other in tables[t] if (min(p, other), max(p, other)) in met_pairs)
                    if conflicts == 0:
                        safe_tables.append(t)
                if safe_tables:
                    candidates = safe_tables

                # Score fin: conflits minimaux puis équilibre
                best_t = None
                best_score = (10**9, 10**9, 10**9)
                for t in candidates:
                    conflicts = sum(1 for other in tables[t] if (min(p, other), max(p, other)) in met_pairs)
                    revisit_penalty = 0 if t not in seen_tables[p] else 1
                    fill = len(tables[t])
                    score = (conflicts, revisit_penalty, fill)
                    if score < best_score:
                        best_score = score
                        best_t = t

                if best_t is None:
                    # Aucun choix viable -> on se rabat sur la table la moins pleine
                    best_t = min(available_tables, key=lambda t: len(tables[t]))

                tables[best_t].append(p)
                seen_tables[p].add(best_t)
                sessions_played[p] += 1

            # Mise à jour des rencontres après placement complet
            for t in range(T):
                ppl = tables[t]
                for i in range(len(ppl)):
                    for j in range(i + 1, len(ppl)):
                        a, b = sorted((ppl[i], ppl[j]))
                        met_pairs[(a, b)] += 1
                        meets_count[a].add(b)
                        meets_count[b].add(a)

            plan.append(tables)

        # faisabilité disponible en attribut pour inspection éventuelle
        self.feasible = feasible
        return plan
