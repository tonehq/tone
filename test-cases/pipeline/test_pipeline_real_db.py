"""Test that the pipeline builds correct services from DB (PipelineParams + service_factory).

Run:
    pytest test-cases/pipeline/test_pipeline_real_db.py -v -s -o "addopts="
"""

import os
import unittest

from dotenv import load_dotenv

load_dotenv(override=True)

from shared.config import settings

SKIP_REASON = ""
if not settings.DATABASE_URL:
    SKIP_REASON = "DATABASE_URL not set"

TEST_AGENT_NAME = "Google Agent"


@unittest.skipIf(SKIP_REASON, SKIP_REASON)
class TestPipelineFromDB(unittest.IsolatedAsyncioTestCase):

    async def test_pipeline_builds_services_from_db(self):
        """Verify PipelineParams + service_factory build LLM/STT/TTS from existing DB data."""
        from sqlalchemy import create_engine, inspect
        from sqlalchemy.exc import OperationalError, ProgrammingError
        from sqlalchemy.orm import sessionmaker
        from core.models.agent import Agent
        from core.services.pipeline import PipelineParams
        from core.services.pipeline.service_factory import build_llm, build_stt, build_tts

        engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

        # Pre-flight: this integration test needs the configured DATABASE_URL to point at
        # a DB carrying THIS codebase's schema. If the DB is unreachable, or it's a foreign/
        # outdated schema (e.g. missing the columns the Agent model expects), skip rather
        # than fail with a confusing SQL error — the test stays meaningful against a real,
        # migrated bamako DB and is a clean skip everywhere else.
        try:
            insp = inspect(engine)
            if "agents" not in insp.get_table_names():
                self.skipTest("DB has no 'agents' table — run `alembic upgrade head` against a bamako DB")
            agent_cols = {c["name"] for c in insp.get_columns("agents")}
            required_cols = {"uuid", "status"}
            missing = required_cols - agent_cols
            if missing:
                self.skipTest(
                    f"DATABASE_URL points at an incompatible schema (agents missing {sorted(missing)}). "
                    "Point it at a migrated bamako DB (`alembic upgrade head` + `python dev/seed.py`)."
                )
        except OperationalError as e:
            self.skipTest(f"DB unreachable: {e}")

        Session = sessionmaker(bind=engine)
        db = Session()
        try:
            agent = db.query(Agent).filter(Agent.name == TEST_AGENT_NAME, Agent.status == "active").first()
            if not agent:
                agent = db.query(Agent).filter(Agent.status == "active").first()
            self.assertIsNotNone(agent, "No active agent found — run `python dev/seed.py`")

            params = PipelineParams.from_agent(agent, db)
            self.assertIsNotNone(params, "PipelineParams.from_agent returned None")

            llm = build_llm(params.llm) if params.llm else None
            stt = build_stt(params.stt) if params.stt else None
            tts = build_tts(params.tts) if params.tts else None
            self.assertIsNotNone(llm, "LLM should be built")
            self.assertIsNotNone(stt, "STT should be built")
            self.assertIsNotNone(tts, "TTS should be built")

            print(f"\n  Agent: id={agent.id} name={agent.name}")
            print(f"  LLM:   {type(llm).__name__}")
            print(f"  STT:   {type(stt).__name__}")
            print(f"  TTS:   {type(tts).__name__}")
            print(f"  Messages: {params.messages}")
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
