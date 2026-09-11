from __future__ import annotations

import copy
import json
import sqlite3
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
import http.cookiejar
from datetime import date
from pathlib import Path

from agente_mantenimiento.analysis import analyze_week
from agente_mantenimiento.database import DuplicateWeekError, HistoryDatabase
from agente_mantenimiento.llm_contract import LLMFindingValidationError, build_llm_context, import_llm_findings
from agente_mantenimiento.llm_openai import INSTRUCTIONS, SYSTEM_PROMPT_PATH, interpret_week_with_openai
from agente_mantenimiento.report import generate_report
from agente_mantenimiento.privacy import detect_confidential_reason, scan_workbook
from agente_mantenimiento.web import AppHandler
import agente_mantenimiento.web as web_module
from http.server import ThreadingHTTPServer
from unittest.mock import patch


PROJECT = Path(__file__).resolve().parents[1]
INPUTS = PROJECT.parent / "2-Trabajo a entregar" / "Archivos excel para cargar"


def analysis_for(week: int) -> dict:
    if week == 33:
        return analyze_week(
            year=2026, week=33, start_date=date(2026, 8, 10), end_date=date(2026, 8, 16),
            notices_path=INPUTS / "33-Avisos MG (1).XLSX",
            notifications_path=INPUTS / "33-Notificaciones (1).XLSX",
            maintenance_path=INPUTS / "33-TAREAS EN SALA SEMANA 33 (1).xlsx",
        )
    return analyze_week(
        year=2026, week=34, start_date=date(2026, 8, 17), end_date=date(2026, 8, 23),
        notices_path=INPUTS / "34-Avisos semana.XLSX",
        notifications_path=INPUTS / "34-Notificaciones.XLSX",
        maintenance_path=INPUTS / "34-TAREAS EN SALA SEMANA.xlsx",
    )


class HistoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db_path = self.root / "history.sqlite3"
        self.db = HistoryDatabase(self.db_path)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_first_week_works_and_reports_insufficient_history(self) -> None:
        result = analysis_for(33)
        self.db.save_analysis(result)
        report = generate_report(
            self.db_path, year=2026, week=33, output_path=self.root / "week33.html"
        )
        content = report.read_text(encoding="utf-8")
        self.assertAlmostEqual(result["global"]["availability"], 94.39587737843553)
        self.assertIn("Sin historial suficiente", content)
        self.assertIn("Corrida incompleta: interpretación LLM pendiente", content)
        self.assertIn("Serie A", content)
        self.assertIn("Sala 1", content)
        self.assertIn('id="tab-history"', content)

    def test_llm_context_is_limited_to_six_previous_weeks(self) -> None:
        base = analysis_for(33)
        for week in range(25, 33):
            item = copy.deepcopy(base)
            item["period"] = {
                "year": 2026, "week": week,
                "start_date": f"2026-07-{week - 20:02d}",
                "end_date": f"2026-07-{week - 14:02d}",
            }
            self.db.save_analysis(item)
        context = build_llm_context(self.db_path, year=2026, week=32)
        periods = [(row["year"], row["week"]) for row in context["history_window"]["included_periods"]]
        self.assertEqual(periods, [(2026, week) for week in range(26, 33)])
        self.assertNotIn(25, {row["week"] for row in context["failure_facts"]})
        self.assertEqual(context["history_window"]["maximum_previous_weeks"], 6)

    def test_second_week_uses_stored_history_and_prepares_filters(self) -> None:
        self.db.save_analysis(analysis_for(33))
        self.db.save_analysis(analysis_for(34))
        report = generate_report(
            self.db_path, year=2026, week=34, output_path=self.root / "week34.html"
        )
        content = report.read_text(encoding="utf-8")
        weeks = self.db.list_weeks()
        self.assertEqual([row["week"] for row in weeks], [33, 34])
        self.assertAlmostEqual(weeks[-1]["global_availability"], 96.68843683083512)
        for expected in (
            'value="2026-33"', 'value="2026-34"', 'id="filter-equipment"',
            'id="filter-room"', 'id="filter-series"', "Horas de parada por semana",
            "Disponibilidad por semana", "Detenciones por semana",
            "Fallas repetidas en el mismo puente", "Candidatos de fallas similares entre puentes",
        ):
            self.assertIn(expected, content)

    def test_duplicate_week_is_rejected_without_changing_history(self) -> None:
        result = analysis_for(33)
        self.db.save_analysis(result)
        with self.assertRaises(DuplicateWeekError):
            self.db.save_analysis(result)
        self.assertEqual(len(self.db.list_weeks()), 1)

    def test_llm_contract_rejects_metrics_and_unknown_notices(self) -> None:
        result = analysis_for(33)
        self.db.save_analysis(result)
        notices = [row["notice_number"] for row in result["failures"][:2]]
        valid = {
            "findings": [{
                "relation_type": "cross_bridge", "title": "Patrón textual a revisar",
                "notice_numbers": notices, "confidence": "media",
                "rationale": "Las descripciones usan términos semejantes.",
                "human_review": "Confirmar con ingeniería de mantenimiento.",
            }]
        }
        valid_path = self.root / "valid.json"
        valid_path.write_text(json.dumps(valid, ensure_ascii=False), encoding="utf-8")
        self.assertEqual(import_llm_findings(self.db_path, valid_path), 1)
        report = generate_report(
            self.db_path, year=2026, week=33, output_path=self.root / "with_llm.html"
        ).read_text(encoding="utf-8")
        self.assertIn("Interpretación preliminar del LLM", report)
        self.assertIn("No es determinante", report)
        self.assertIn("revisión y validación humana", report)

        invalid = json.loads(json.dumps(valid))
        invalid["findings"][0]["availability"] = 99.9
        invalid_path = self.root / "invalid.json"
        invalid_path.write_text(json.dumps(invalid), encoding="utf-8")
        with self.assertRaises(LLMFindingValidationError):
            import_llm_findings(self.db_path, invalid_path)

        invalid = json.loads(json.dumps(valid))
        invalid["findings"][0]["notice_numbers"] = [notices[0], "NO-EXISTE"]
        invalid_path.write_text(json.dumps(invalid), encoding="utf-8")
        with self.assertRaises(LLMFindingValidationError):
            import_llm_findings(self.db_path, invalid_path)

    def test_database_contains_structured_weekly_rows(self) -> None:
        self.db.save_analysis(analysis_for(33))
        connection = sqlite3.connect(self.db_path)
        try:
            self.assertEqual(connection.execute("SELECT count(*) FROM weeks").fetchone()[0], 1)
            self.assertEqual(connection.execute("SELECT count(*) FROM equipment_week").fetchone()[0], 12)
            self.assertEqual(connection.execute("SELECT count(*) FROM aggregate_week").fetchone()[0], 6)
            self.assertGreater(connection.execute("SELECT count(*) FROM failure_events").fetchone()[0], 0)
            self.assertGreater(connection.execute("SELECT count(*) FROM maintenance_events").fetchone()[0], 0)
        finally:
            connection.close()

    def test_openai_interpretation_uses_schema_and_is_scoped_to_week(self) -> None:
        result = analysis_for(33)
        self.db.save_analysis(result)
        notices = [row["notice_number"] for row in result["failures"][:2]]
        output = {
            "findings": [{
                "relation_type": "cross_bridge", "title": "Relación preliminar",
                "notice_numbers": notices, "confidence": "baja",
                "rationale": "Los textos presentan una coincidencia funcional a revisar.",
                "human_review": "Validar la asociación con el responsable técnico.",
            }]
        }

        def transport(body: dict, key: str) -> dict:
            self.assertEqual(key, "test-key")
            self.assertEqual(body["instructions"], SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip())
            self.assertEqual(body["text"]["format"]["type"], "json_schema")
            self.assertTrue(body["text"]["format"]["strict"])
            self.assertNotIn("availability", body["input"])
            return {"output_text": json.dumps(output, ensure_ascii=False)}

        count = interpret_week_with_openai(
            self.db_path, year=2026, week=33, api_key="test-key", transport=transport
        )
        self.assertEqual(count, 1)
        report_data = self.db.load_report_data(2026, 33)
        self.assertEqual(len(report_data["llm_findings"]), 1)

    def test_openai_usage_and_cost_are_recorded(self) -> None:
        result = analysis_for(33)
        self.db.save_analysis(result)
        notices = [row["notice_number"] for row in result["failures"][:2]]
        response = {
            "id": "resp_test_cost",
            "output_text": json.dumps({"findings": [{
                "relation_type": "same_bridge", "title": "Repetición preliminar",
                "notice_numbers": notices, "confidence": "media",
                "rationale": "Los textos documentan una similitud.",
                "human_review": "Verificar el equipo en campo.",
            }]}),
            "usage": {
                "input_tokens": 10_000, "output_tokens": 2_000, "total_tokens": 12_000,
                "input_tokens_details": {"cached_tokens": 1_000},
                "output_tokens_details": {"reasoning_tokens": 800},
            },
        }
        interpret_week_with_openai(
            self.db_path, year=2026, week=33, api_key="test", model="gpt-5.4-mini",
            reasoning_effort="high", transport=lambda body, key: response,
        )
        run = self.db.list_llm_runs()[0]
        self.assertEqual(run["reasoning_effort"], "high")
        self.assertEqual(run["reasoning_tokens"], 800)
        self.assertAlmostEqual(run["total_cost_usd"], 0.015825)

    def test_archive_keeps_exact_prompts_and_execution_metadata(self) -> None:
        self.assertEqual(INSTRUCTIONS, SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip())
        for section in (
            "## 1. Rol", "## 2. Contexto", "## 3. Tarea",
            "## 4. Fuentes y restricciones", "## 5. Formato de salida",
            "## 6. Ejemplos de criterio",
        ):
            self.assertIn(section, INSTRUCTIONS)
        result = analysis_for(33)
        self.db.save_analysis(result)
        report = generate_report(
            self.db_path, year=2026, week=33, output_path=self.root / "week33.html"
        )
        archive_dir = self.root / "corridas"
        with patch.object(web_module, "DEFAULT_ARCHIVE_DIR", archive_dir):
            web_module._save_archive(
                result, 2026, 33, report,
                database_path=self.db_path,
                requested_model="gpt-5.4-mini",
                requested_effort="medium",
                llm_error="LLM pendiente",
            )
        roots = list(archive_dir.glob("corrida_*_semana_33"))
        self.assertEqual(len(roots), 1)
        root = roots[0]
        for relative in (
            "README.md", "METADATA.json", "entrada/ARCHIVOS.md",
            "prompts/SYSTEM_PROMPT.txt", "prompts/USER_PROMPT.txt",
            "prompts/USER_PROMPT_TEMPLATE.md", "prompts/CONTRATO_FUNCIONAL_AGENTE.md",
            "salida/resultados.json", "salida/contexto_llm.json",
            "salida/hallazgos_llm.json", "salida/ejecuciones_llm.json",
            "salida/Reporte_Disponibilidad_Semana33.html", "validacion/VALIDACION.md",
        ):
            self.assertTrue((root / relative).is_file(), relative)
        metadata = json.loads((root / "METADATA.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["llm_status"], "pending")
        self.assertEqual(metadata["requested_model"], "gpt-5.4-mini")
        self.assertEqual(metadata["source_sha256"]["notices"], result["sources"]["notices"]["sha256"])
        notices = [row["notice_number"] for row in result["failures"][:2]]
        payload = self.root / "archive-findings.json"
        payload.write_text(json.dumps({"findings": [{
            "relation_type": "cross_bridge", "title": "Relación preliminar",
            "notice_numbers": notices, "confidence": "baja",
            "rationale": "Los textos requieren comparación técnica.",
            "human_review": "Validar antes de concluir.",
        }]}, ensure_ascii=False), encoding="utf-8")
        import_llm_findings(self.db_path, payload, year=2026, week=33)
        with patch.object(web_module, "DEFAULT_ARCHIVE_DIR", archive_dir):
            web_module._refresh_archived_reports(self.db_path, 2026, 33)
        refreshed = json.loads((root / "METADATA.json").read_text(encoding="utf-8"))
        self.assertEqual(refreshed["llm_status"], "completed")
        self.assertIn("Estado LLM: `completed`", (root / "README.md").read_text(encoding="utf-8"))

    def test_web_upload_processes_week_and_rejects_duplicate(self) -> None:
        original_database_path = AppHandler.database_path
        AppHandler.database_path = self.db_path
        output_patch = patch.object(web_module, "DEFAULT_OUTPUT_DIR", self.root / "web-output")
        output_patch.start()
        server = ThreadingHTTPServer(("127.0.0.1", 0), AppHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"

        def multipart() -> tuple[bytes, str]:
            boundary = "----codex-maintenance-test"
            pieces: list[bytes] = []
            for name, value in (
                ("year", "2026"), ("week", "33"),
                ("start_date", "2026-08-10"), ("end_date", "2026-08-16"),
            ):
                pieces.append(
                    f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode()
                )
            for name, filename in (
                ("notices", "33-Avisos MG (1).XLSX"),
                ("notifications", "33-Notificaciones (1).XLSX"),
                ("maintenance", "33-TAREAS EN SALA SEMANA 33 (1).xlsx"),
            ):
                payload = (INPUTS / filename).read_bytes()
                pieces.append(
                    f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"; filename=\"{filename}\"\r\nContent-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n".encode()
                    + payload + b"\r\n"
                )
            pieces.append(f"--{boundary}--\r\n".encode())
            return b"".join(pieces), f"multipart/form-data; boundary={boundary}"

        try:
            with urllib.request.urlopen(base + "/", timeout=10) as response:
                self.assertIn("Nueva semana", response.read().decode("utf-8"))
            body, content_type = multipart()
            request = urllib.request.Request(
                base + "/procesar", data=body, headers={"Content-Type": content_type}, method="POST"
            )
            with patch.object(web_module, "interpret_week_with_openai", side_effect=web_module.LLMServiceError("LLM pendiente")), patch.object(web_module, "_save_archive"):
                try:
                    with urllib.request.urlopen(request, timeout=20) as response:
                        content = response.read().decode("utf-8")
                except urllib.error.HTTPError as error:
                    self.fail(error.read().decode("utf-8"))
                self.assertIn("Semana 33/2026 calculada y guardada", content)
                self.assertIn("LLM pendiente", content)
            self.assertTrue(self.db.week_exists(2026, 33))
            with urllib.request.urlopen(base + "/reporte?year=2026&week=33", timeout=10) as response:
                self.assertIn(
                    "Corrida incompleta: interpretación LLM pendiente",
                    response.read().decode("utf-8"),
                )
            with self.assertRaises(urllib.error.HTTPError) as duplicate:
                urllib.request.urlopen(request, timeout=20)
            self.assertEqual(duplicate.exception.code, 409)
            self.assertEqual(len(self.db.list_weeks()), 1)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
            AppHandler.database_path = original_database_path
            output_patch.stop()

    def test_public_web_requires_password_and_creates_session(self) -> None:
        original = (AppHandler.database_path, AppHandler.password, AppHandler.session_secret)
        AppHandler.database_path = self.db_path
        AppHandler.password = "una-clave-segura-de-prueba"
        AppHandler.session_secret = "s" * 40
        server = ThreadingHTTPServer(("127.0.0.1", 0), AppHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        try:
            with self.assertRaises(urllib.error.HTTPError) as unauthorized:
                opener.open(base + "/", timeout=10)
            self.assertEqual(unauthorized.exception.code, 401)
            login = urllib.parse.urlencode({"password": "una-clave-segura-de-prueba"}).encode()
            with opener.open(urllib.request.Request(base + "/login", data=login), timeout=10) as response:
                self.assertIn("Nueva semana", response.read().decode("utf-8"))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
            AppHandler.database_path, AppHandler.password, AppHandler.session_secret = original

    def test_public_binding_rejects_missing_security_secrets(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(RuntimeError):
                web_module.serve("0.0.0.0", 0, self.db_path)

    def test_privacy_filter_rejects_personal_data_and_accepts_technical_ids(self) -> None:
        self.assertIsNotNone(detect_confidential_reason("Juan López", "Descripción"))
        self.assertIsNotNone(detect_confidential_reason("12345", "Observación"))
        self.assertIsNotNone(detect_confidential_reason("30123456", "DNI"))
        self.assertIsNotNone(detect_confidential_reason("persona@empresa.com", "Texto"))
        self.assertIsNotNone(detect_confidential_reason("Tel: +54 280 4123456", "Texto"))
        self.assertIsNone(detect_confidential_reason("P-MG11", "Equipo"))
        self.assertIsNone(detect_confidential_reason("800901669", "Aviso"))
        self.assertIsNone(detect_confidential_reason("11306655", "Orden"))
        self.assertIsNone(detect_confidential_reason("turno C", "Observación"))

        class Sheet:
            title = "Datos"
            def iter_rows(self, values_only: bool = True):
                return iter([("Equipo", "Operario"), ("P-MG11", "Juan López")])

        class Workbook:
            worksheets = [Sheet()]
            def close(self):
                pass

        with patch("agente_mantenimiento.privacy.openpyxl.load_workbook", return_value=Workbook()):
            locations = scan_workbook(self.root / "privado.xlsx", display_name="privado.xlsx")
        self.assertEqual(len(locations), 1)
        self.assertEqual(locations[0].column, "B")
        self.assertNotIn("Juan", str(locations[0]))


if __name__ == "__main__":
    unittest.main()
