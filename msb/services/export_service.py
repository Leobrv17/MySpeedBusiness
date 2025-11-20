from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


@dataclass
class BadgeInfo:
    participant_id: int
    full_name: str
    job: str
    is_guest: bool
    tables: list[str]


class ExportService:
    """Service d'export (Excel, PDF Badges)."""

    def __init__(self, persistence=None, logo_path: Path | None = None) -> None:
        self.persistence = persistence
        self.logo_path = logo_path

    def export_excel(self) -> None:
        # TODO: à implémenter
        pass

    def export_badges_pdf(self, output_path: str | Path) -> Path:
        """
        Génère un PDF contenant un badge par participant.

        Format demandé :
        - Nom de la réunion + logo BNI
        - Nom & prénom, métier, suffixe « (Invité) » si applicable
        - Table assignée pour chaque session, dans l'ordre
        """
        persistence = self._require_persistence()
        output_path = Path(output_path)

        event_info = persistence.get_event_info()
        participants = list(persistence.list_participants())
        plan = persistence.load_plan()

        session_count = event_info.get("session_count") or 0
        session_count = max(session_count, len(plan)) if plan else session_count

        badges = self._build_badges(participants, plan, session_count)
        logo = self._resolve_logo_path()

        self._render_badges(
            output_path=output_path,
            event_name=event_info.get("name", ""),
            badges=badges,
            logo_path=logo,
        )
        return output_path

    # --- helpers ---------------------------------------------------------
    def _require_persistence(self):
        if not self.persistence:
            raise RuntimeError("Persistence non fournie pour l'export")
        return self.persistence

    def _resolve_logo_path(self) -> Path | None:
        if self.logo_path:
            return Path(self.logo_path)
        default = Path(__file__).resolve().parents[2] / "img" / "bni_logo.png"
        return default if default.exists() else None

    def _build_badges(self, participants: Iterable, plan: list, session_count: int) -> list[BadgeInfo]:
        tables_by_participant = {
            p.id: ["-"] * session_count for p in participants
        } if session_count > 0 else {p.id: [] for p in participants}

        for s_idx, tables in enumerate(plan or []):
            if s_idx >= session_count:
                break
            for t_idx, pids in enumerate(tables):
                for pid in pids:
                    if pid in tables_by_participant:
                        tables_by_participant[pid][s_idx] = str(t_idx + 1)

        badges: list[BadgeInfo] = []
        for p in participants:
            full_name = f"{p.first_name} {p.last_name}"
            badges.append(
                BadgeInfo(
                    participant_id=p.id,
                    full_name=full_name,
                    job=p.job,
                    is_guest=bool(getattr(p, "is_guest", False)),
                    tables=tables_by_participant.get(p.id, []),
                )
            )
        return badges

    def _render_badges(
        self,
        *,
        output_path: Path,
        event_name: str,
        badges: list[BadgeInfo],
        logo_path: Path | None,
    ) -> None:
        c = canvas.Canvas(str(output_path), pagesize=A4)
        width, height = A4
        margin = 20 * mm

        logo_reader = None
        logo_max_width = 45 * mm
        logo_max_height = 20 * mm
        if logo_path and logo_path.exists():
            logo_reader = ImageReader(str(logo_path))

        for badge in badges:
            y = height - margin

            # Titre de réunion
            c.setFont("Helvetica-Bold", 18)
            c.drawString(margin, y, event_name)

            if logo_reader:
                c.drawImage(
                    logo_reader,
                    width - margin - logo_max_width,
                    height - margin - logo_max_height,
                    width=logo_max_width,
                    height=logo_max_height,
                    preserveAspectRatio=True,
                    mask="auto",
                )

            y -= 30
            name_line = badge.full_name
            if badge.is_guest:
                name_line = f"{name_line} (Invité)"
            c.setFont("Helvetica-Bold", 24)
            c.drawString(margin, y, name_line)

            y -= 18
            c.setFont("Helvetica", 14)
            c.drawString(margin, y, badge.job)

            y -= 26
            c.setFont("Helvetica-Bold", 14)
            c.drawString(margin, y, "Tables par session :")
            y -= 16
            c.setFont("Helvetica", 12)

            if not badge.tables:
                c.drawString(margin, y, "Aucun plan de table enregistré.")
            else:
                for idx, table in enumerate(badge.tables, start=1):
                    c.drawString(margin, y, f"Session {idx} : Table {table}")
                    y -= 14

            c.showPage()

        c.save()
