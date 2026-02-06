"""
Minimal test script - Copy this to your project and run directly.

Usage:
    python test_minimal.py
"""

import asyncio

async def main():
    # ========== 1. DATABASE ==========
    from core.database.session import SessionLocal  # Adjust import path
    db = SessionLocal()
    
    # ========== 2. AGENT ==========
    from core.models.agent import Agent
    AGENT_ID = 11  # <-- CHANGE THIS
    agent = db.query(Agent).filter(Agent.id == AGENT_ID).first()
    print(f"Agent: {agent}")
    
    # ========== 3. TRANSPORT (Mock) ==========
    # Pipeline expects transport.input() and transport.output() to return FrameProcessor
    # instances (they must have .link() and ._prev / ._next). Use minimal subclasses.
    from pipecat.processors.frame_processor import FrameProcessor

    class MockPipelineInput(FrameProcessor):
        def __init__(self):
            super().__init__(name="MockInput")

    class MockPipelineOutput(FrameProcessor):
        def __init__(self):
            super().__init__(name="MockOutput")

    class MockTransport:
        def input(self):
            return MockPipelineInput()
        def output(self):
            return MockPipelineOutput()
        def event_handler(self, name):
            def decorator(func):
                return func
            return decorator

    transport = MockTransport()
    
    # ========== 4. RUNNER ARGS ==========
    class RunnerArgs:
        handle_sigint = False
    
    runner_args = RunnerArgs()
    
    # ========== 5. RUN TEST ==========
    from core.services.agent_factory_service import AgentFactoryService
    
    service = AgentFactoryService(db)
    
    try:
        # Debug: Check each step
        print("\n--- Debug Info ---")
        config = service._get_agent_config(agent)
        # print(f"Config: {config}")
        # print(f"LLM Service ID: {config.llm_service_id if config else None}")
        # print(f"STT Service ID: {config.stt_service_id if config else None}")
        # print(f"TTS Service ID: {config.tts_service_id if config else None}")
        
        llm = service.get_llm_for_agent(agent)
        # print(f"LLM: {llm}")
        
        stt = service.get_stt_for_agent(agent)
        # print(f"STT: {stt}")
        
        tts = service.get_tts_for_agent(agent)
        # print(f"TTS: {tts}")
        
        bot_data = service.get_agent_bot_data(agent)
        print(f"Bot Data: {bot_data}")
        
        print("\n--- Running run_bot_for_agent ---")
        await service.run_bot_for_agent(agent, transport, runner_args)
        print("SUCCESS!")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
