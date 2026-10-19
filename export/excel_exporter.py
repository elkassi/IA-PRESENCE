"""
Excel Exporter — Export quotidien des présences au format Excel (.xlsx).

Fichier généré : ``exports/YYYY-MM-DD_presence.xlsx``

Colonnes : Nom | Heure d'arrivée | Statut | Date

Formatage :
    - En-tête : fond violet ``#7c3aed``, texte blanc, gras.
    - Lignes alternées : blanc / violet clair ``#f5f3ff``.
    - Badge statut : vert pour IN_TIME, orange pour LATE.
    - Largeurs de colonnes auto-ajustées.
    - Ligne de résumé en bas.

Contrainte : export en < 5 secondes pour 100 enregistrements.
"""

import os
import logging
from datetime import date, datetime
from typing import Optional

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import EXPORTS_DIR
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class ExcelExporter:
    """Exporteur de rapports de présence au format Excel.

    Attributes:
        _db: Instance du gestionnaire de base de données.
        _exports_dir: Répertoire de sortie des fichiers Excel.
    """

    # Styles
    HEADER_FILL = PatternFill(start_color="7c3aed", end_color="7c3aed", fill_type="solid")
    HEADER_FONT = Font(name="Calibri", bold=True, color="FFFFFF", size=12)
    ALT_ROW_FILL = PatternFill(start_color="f5f3ff", end_color="f5f3ff", fill_type="solid")
    IN_TIME_FILL = PatternFill(start_color="10b981", end_color="10b981", fill_type="solid")
    IN_TIME_FONT = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
    LATE_FILL = PatternFill(start_color="f59e0b", end_color="f59e0b", fill_type="solid")
    LATE_FONT = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
    NORMAL_FONT = Font(name="Calibri", size=11)
    SUMMARY_FONT = Font(name="Calibri", bold=True, size=12)
    SUMMARY_FILL = PatternFill(start_color="e0e7ff", end_color="e0e7ff", fill_type="solid")
    CENTER_ALIGN = Alignment(horizontal="center", vertical="center")
    LEFT_ALIGN = Alignment(horizontal="left", vertical="center")
    THIN_BORDER = Border(
        left=Side(style="thin", color="d1d5db"),
        right=Side(style="thin", color="d1d5db"),
        top=Side(style="thin", color="d1d5db"),
        bottom=Side(style="thin", color="d1d5db"),
    )

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialise l'exporteur.

        Args:
            db_manager: Instance de ``DatabaseManager``.
        """
        self._db = db_manager
        self._exports_dir = EXPORTS_DIR
        os.makedirs(self._exports_dir, exist_ok=True)
        logger.info("ExcelExporter initialisé (dossier=%s).", self._exports_dir)

    def export_today(self, export_date: Optional[date] = None) -> str:
        """Exporte les présences du jour en fichier Excel.

        Args:
            export_date: Date à exporter. Par défaut, aujourd'hui.

        Returns:
            Chemin absolu du fichier Excel généré.
        """
        target_date = export_date or date.today()
        filename = f"{target_date.strftime('%Y-%m-%d')}_presence.xlsx"
        filepath = os.path.join(self._exports_dir, filename)

        logger.info("Début export Excel pour le %s…", target_date)

        # Récupérer les données
        records = self._db.get_today_attendance()
        stats = self._db.get_stats_today()

        # Créer le classeur
        wb = Workbook()
        ws = wb.active
        # openpyxl interdit certains caractères dans les noms de feuilles
        # (ex: "/" ":" "\" "?" "*" "[" "]"). On utilise donc un format safe.
        ws.title = f"Présences {target_date.strftime('%d-%m-%Y')}"

        # Titre
        ws.merge_cells("A1:E1")
        title_cell = ws["A1"]
        title_cell.value = f"📋 Rapport de Présence — {target_date.strftime('%d/%m/%Y')}"
        title_cell.font = Font(name="Calibri", bold=True, size=16, color="7c3aed")
        title_cell.alignment = self.CENTER_ALIGN
        ws.row_dimensions[1].height = 40

        # Ligne vide
        ws.row_dimensions[2].height = 10

        # En-têtes
        headers = ["Nom", "Heure d'arrivée", "Statut", "Date", "Classe"]
        header_row = 3
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=header_row, column=col_idx, value=header)
            cell.fill = self.HEADER_FILL
            cell.font = self.HEADER_FONT
            cell.alignment = self.CENTER_ALIGN
            cell.border = self.THIN_BORDER

        ws.row_dimensions[header_row].height = 30

        # Données
        for row_idx, record in enumerate(records, header_row + 1):
            # Nom
            name_cell = ws.cell(row=row_idx, column=1, value=record["name"])
            name_cell.font = self.NORMAL_FONT
            name_cell.alignment = self.LEFT_ALIGN
            name_cell.border = self.THIN_BORDER

            # Heure d'arrivée
            try:
                ts = datetime.fromisoformat(record["timestamp"])
                time_str = ts.strftime("%H:%M:%S")
            except (ValueError, TypeError):
                time_str = str(record["timestamp"])

            time_cell = ws.cell(row=row_idx, column=2, value=time_str)
            time_cell.font = self.NORMAL_FONT
            time_cell.alignment = self.CENTER_ALIGN
            time_cell.border = self.THIN_BORDER

            # Statut (badge coloré)
            status = record["status"]
            status_cell = ws.cell(row=row_idx, column=3, value=status)
            status_cell.alignment = self.CENTER_ALIGN
            status_cell.border = self.THIN_BORDER
            if status == "IN_TIME":
                status_cell.fill = self.IN_TIME_FILL
                status_cell.font = self.IN_TIME_FONT
            else:
                status_cell.fill = self.LATE_FILL
                status_cell.font = self.LATE_FONT

            # Date
            date_cell = ws.cell(
                row=row_idx, column=4,
                value=target_date.strftime("%d/%m/%Y"),
            )
            date_cell.font = self.NORMAL_FONT
            date_cell.alignment = self.CENTER_ALIGN
            date_cell.border = self.THIN_BORDER

            # Classe
            class_cell = ws.cell(
                row=row_idx, column=5,
                value=record.get("class_number", "") or "",
            )
            class_cell.font = self.NORMAL_FONT
            class_cell.alignment = self.CENTER_ALIGN
            class_cell.border = self.THIN_BORDER

            # Ligne alternée
            if row_idx % 2 == 0:
                for col in range(1, 6):
                    cell = ws.cell(row=row_idx, column=col)
                    if col != 3:  # Ne pas écraser le style du statut
                        cell.fill = self.ALT_ROW_FILL

            ws.row_dimensions[row_idx].height = 25

        # Ligne de résumé
        summary_row = header_row + len(records) + 2
        ws.merge_cells(f"A{summary_row}:E{summary_row}")
        summary_cell = ws.cell(
            row=summary_row, column=1,
            value=(
                f"📊 Total : {stats['total']}   |   "
                f"✅ IN TIME : {stats['in_time']}   |   "
                f"🟡 LATE : {stats['late']}"
            ),
        )
        summary_cell.font = self.SUMMARY_FONT
        summary_cell.fill = self.SUMMARY_FILL
        summary_cell.alignment = self.CENTER_ALIGN
        ws.row_dimensions[summary_row].height = 35

        # Auto-ajuster les largeurs de colonnes
        column_widths = [30, 20, 15, 15, 12]
        for col_idx, width in enumerate(column_widths, 1):
            ws.column_dimensions[get_column_letter(col_idx)].width = width

        # Sauvegarder
        try:
            wb.save(filepath)
            logger.info("Export Excel terminé : %s (%d enregistrements).", filepath, len(records))
            return filepath
        except Exception as e:
            logger.error("Erreur lors de l'export Excel : %s", e)
            raise
