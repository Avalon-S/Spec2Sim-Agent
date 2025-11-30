import json
import asyncio
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.genai import types
from google.genai.errors import ServerError, ClientError
from core import config

class AnalystAgent:
    def __init__(self):
        pass

    async def extract_spec(self, text: str) -> dict:
        # Initialize agent and runner inside the method to ensure they are tied to the current asyncio loop
        # This prevents "WinError 6" and other asyncio loop reuse issues on Windows
        agent = LlmAgent(
            name='analyst_agent',
            model=Gemini(
                model=config.MODEL_NAME, 
                generation_config=config.GENERATION_CONFIG,
                retry_options=config.RETRY_OPTIONS
            ),
            description="Analyzes system descriptions to extract specifications.",
            instruction="""
            You are an expert system analyst. Analyze the provided system description and extract the specification in JSON format.
            
            Output JSON format:
            {
              "states": [{"name": "..."}],
              "transitions": [{"from": "...", "to": "...", "condition": "..."}],
              "constraints": [{"param": "...", "value": "..."}]
            }
            
            IMPORTANT:
            - If a transition condition involves time (e.g., "30s elapsed", "wait 10 mins"), you MUST extract that duration as a constraint.
            - Example: "Red -> Green after 30s" should result in:
              - Transition condition: "30s elapsed"
              - Constraint: {"param": "Red_duration", "value": 30}
            
            Return ONLY the JSON object.
            """
        )
        runner = InMemoryRunner(agent=agent)

        try:
            # Run the runner directly since we are now in an async method
            # Native retry logic in Gemini model will handle 503/429 errors
            response = await runner.run_debug(text)
        except Exception as e:
            print(f"[ERROR] Unexpected error in AnalystAgent: {e}")
            return {}

        # response is a list of Turn objects from the ADK runner
        text_response = ""
        try:
            if response and len(response) > 0:
                last_turn = response[-1]
                if hasattr(last_turn, 'content') and last_turn.content and last_turn.content.parts:
                    text_response = last_turn.content.parts[0].text
            
            if not text_response:
                text_response = str(response)

            # Clean up potential markdown
            if "```json" in text_response:
                import re
                match = re.search(r'```json\s*(\{.*?\})\s*```', text_response, re.DOTALL)
                if match:
                    text_response = match.group(1)
                else:
                    # Fallback cleanup
                    text_response = text_response.replace("```json", "").replace("```", "")
            
            return json.loads(text_response.strip())
        except Exception as e:
            print(f"Error parsing JSON from Analyst Agent: {e}")
            print(f"Raw response: {text_response}")
            return {}
