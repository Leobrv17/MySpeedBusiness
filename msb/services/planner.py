from __future__ import annotations
import random
from typing import List, Dict, Set
from msb.domain.models import Event, SeatingPlan

class Planner:
    """
    Heuristique simple:
    - Répartit les participants aux tables par session
    - Essaie de minimiser les re-rencontres (pairwise)
    NB: Ce n'est pas un solveur exact; on vise un plan plausible pour la démo UI.
    """

    def build_plan(self, event: Event) -> SeatingPlan:
        if not event or not event.participants:
            return SeatingPlan(event_id=event.id, plan=[])

        S = event.session_count or 0
        T = event.num_tables or 0
        if S <= 0 or T <= 0:
            return SeatingPlan(event_id=event.id, plan=[])

        # Shuffle participants for diversité
        participants = list(event.participants)
        random.shuffle(participants)

        # Historique des rencontres: pair_id -> sessions_count
        met: Dict[frozenset[int], int] = {}

        # build seats: sessions -> tables -> list of pids
        plan: List[List[List[int]]] = []
        per_table_target = max(event.table_capacity_min, min(event.table_capacity_max, max(1, len(participants)//max(1,T) + (1 if len(participants)%T else 0))))

        for s in range(S):
            session_tables: List[List[int]] = [[] for _ in range(T)]
            for p in participants:
                # Choisir la table minimisant les re-rencontres
                best_idx = None
                best_score = 1e9
                for t_idx in range(T):
                    if len(session_tables[t_idx]) >= per_table_target:
                        continue
                    # score = nb rencontres existantes avec gens déjà assis
                    score = 0
                    for other in session_tables[t_idx]:
                        pair = frozenset((p.id, other))
                        score += met.get(pair, 0)
                    if score < best_score:
                        best_score = score
                        best_idx = t_idx
                if best_idx is None:
                    # si toutes pleines selon target, mettre là où c'est le plus court
                    best_idx = min(range(T), key=lambda i: len(session_tables[i]))
                session_tables[best_idx].append(p.id)

            # update met
            for table in session_tables:
                for i in range(len(table)):
                    for j in range(i+1, len(table)):
                        pair = frozenset((table[i], table[j]))
                        met[pair] = met.get(pair, 0) + 1

            plan.append(session_tables)

            # rotation simple pour éviter stagnation
            random.shuffle(participants)

        return SeatingPlan(event_id=event.id, plan=plan)
