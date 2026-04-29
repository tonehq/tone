"""Test AgentFactoryService builds correct services from DB.

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

    async def test_agent_factory_builds_services_from_db(self):
        """Verify AgentFactoryService correctly builds LLM/STT/TTS from existing DB data."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from core.models.agent import Agent
        from core.services.agent_factory_service import AgentFactoryService

        engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
        Session = sessionmaker(bind=engine)
        db = Session()
        try:
            agent = db.query(Agent).filter(Agent.name == TEST_AGENT_NAME, Agent.status == "active").first()
            if not agent:
                agent = db.query(Agent).filter(Agent.status == "active").first()
            self.assertIsNotNone(agent, "No active agent found — run `python dev/seed.py`")

            factory = AgentFactoryService(db=db)
            bot_data = factory.get_agent_bot_data(agent)
            self.assertIsNotNone(bot_data, "get_agent_bot_data returned None")

            self.assertIsNotNone(bot_data["llm"], "LLM should be built")
            self.assertIsNotNone(bot_data["stt"], "STT should be built")
            self.assertIsNotNone(bot_data["tts"], "TTS should be built")

            print(f"\n  Agent: id={agent.id} name={agent.name}")
            print(f"  LLM:   {type(bot_data['llm']).__name__}")
            print(f"  STT:   {type(bot_data['stt']).__name__}")
            print(f"  TTS:   {type(bot_data['tts']).__name__}")
            print(f"  Messages: {bot_data['messages']}")
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
