"""
Generate an Excel file mapping TTS models to voices (1:1) for testing.

Queries the database for all TTS service providers, their models, and voices,
then creates a one-to-one mapping ensuring each model and voice is used only once.

Usage:
    python scripts/voice_test_latest/generate_voice_test_matrix.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

from core.database.session import get_db_script
from core.models.service_provider import ServiceProvider
from core.models.models import Model
from core.models.voice import Voice

TARGET_PROVIDERS = {
    "Cartesia", "Groq", "Hathora", "MiniMax", "Rime", "Sarvam",
    "Inworld", "OpenAI", "Neuphonic", "LMNT", "Hume AI", "ElevenLabs",
    "Camb AI", "Async AI", "Speechmatics",
}


def generate_voice_test_excel():
    db = get_db_script()
    try:
        # Get all TTS service providers
        providers = (
            db.query(ServiceProvider)
            .filter(ServiceProvider.provider_type == "tts")
            .filter(ServiceProvider.status == "active")
            .all()
        )

        # Filter to target providers only
        providers = [
            p for p in providers if p.display_name in TARGET_PROVIDERS
        ]

        if not providers:
            print("No matching TTS providers found in the database.")
            return

        print(f"Found {len(providers)} TTS provider(s)")

        rows = []

        for provider in providers:
            # Get models for this provider
            models = (
                db.query(Model)
                .filter(Model.service_provider_id == provider.id)
                .filter(Model.status == "active")
                .all()
            )

            # Get voices for this provider
            voices = (
                db.query(Voice)
                .filter(Voice.service_provider_id == provider.id)
                .filter(Voice.is_active == True)
                .all()
            )

            print(
                f"  {provider.display_name}: {len(models)} model(s), {len(voices)} voice(s)"
            )

            if not models or not voices:
                print(f"    Skipping - no models or voices available")
                continue

            # 1:1 mapping - pair each model with a unique voice
            pair_count = min(len(models), len(voices))
            for i in range(pair_count):
                rows.append(
                    {
                        "service_provider_id": provider.id,
                        "service_provider_name": provider.display_name,
                        "model_id": models[i].id,
                        "model_name": models[i].name,
                        "voice_id": voices[i].voice_id or "",
                        "status": "",
                        "call_log_id": "",
                    }
                )

        if not rows:
            print("No model-voice pairs generated.")
            return

        # Create Excel workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Voice Test Matrix"

        headers = [
            "service_provider_id",
            "service_provider_name",
            "model_id",
            "model_name",
            "voice_id",
            "status",
            "call_log_id",
        ]

        # Styles
        header_fill = PatternFill(
            start_color="4472C4", end_color="4472C4", fill_type="solid"
        )
        header_font = Font(bold=True, color="FFFFFF", size=11)
        thin_border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )

        # Write headers
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")
            cell.border = thin_border

        # Write data rows
        for row_idx, row_data in enumerate(rows, 2):
            for col_idx, header in enumerate(headers, 1):
                cell = ws.cell(row=row_idx, column=col_idx, value=row_data[header])
                cell.border = thin_border
                cell.alignment = Alignment(horizontal="center")

        # Auto-fit column widths
        total_rows = len(rows) + 1
        for col in range(1, len(headers) + 1):
            max_length = len(headers[col - 1])
            for r in range(2, total_rows + 1):
                cell_value = ws.cell(row=r, column=col).value
                if cell_value:
                    max_length = max(max_length, len(str(cell_value)))
            ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = min(
                max_length + 4, 50
            )

        # Freeze header row and add auto-filter
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = f"A1:{openpyxl.utils.get_column_letter(len(headers))}{total_rows}"

        # Save
        output_dir = os.path.dirname(os.path.abspath(__file__))
        output_file = os.path.join(output_dir, "Voice_Test_Matrix.xlsx")
        wb.save(output_file)

        print(f"\nExcel file created: {output_file}")
        print(f"Total test pairs: {len(rows)}")

    finally:
        db.close()


if __name__ == "__main__":
    generate_voice_test_excel()
