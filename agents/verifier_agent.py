import json
import asyncio
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.genai.errors import ServerError, ClientError
from core import config
import inspect

class VerifierAgent:
    def __init__(self, tools=None):
        self.tools = tools or []

    async def verify(self, spec: dict, code: str) -> dict:
        # Initialize agent and runner inside the method to ensure they are tied to the current asyncio loop
        agent = LlmAgent(
            name='verifier_agent',
            model=Gemini(
                model=config.MODEL_NAME, 
                generation_config=config.JSON_GENERATION_CONFIG,
                retry_options=config.RETRY_OPTIONS
            ),
            description="Verifies simulation logs against specifications.",
            instruction="""
            You are a QA Verifier. Your goal is to verify if the simulation code matches the specification.

            Process:
            1.  **Execute Code**: Use the `execute_simulation_code` tool to run the provided Python code.
            2.  **Analyze Output**: Examine the returned 'LOGS' and 'ERRORS'.
            3.  **Verify**: Compare the execution logs against the provided Specification.

            Verification Logic:
            1.  **CRITICAL**: If 'ERRORS' contains any Python exceptions (tracebacks), return FAIL with "retry": true immediately.
            2.  **CRITICAL**: If 'LOGS' are empty or do not contain lines starting with `[SIM]`, return FAIL with `retry: true`. This means the simulation failed to run properly.
            3.  If logs show missing transitions defined in spec, return FAIL.
            4.  If constraints in spec are not met (based on logs), return FAIL.
            5.  Otherwise, PASS.
            
            IMPORTANT: 
            - The simulation runs for a fixed time. If the logs end abruptly (e.g., waiting for a state but no transition), THIS IS NORMAL and NOT a failure, provided previous transitions were correct. Do not fail based on the final incomplete state.
            - **USE `print(...)` FOR LOGGING.** Do NOT use the `logging` module, as it may not be captured correctly. Ensure all logs start with `[SIM]`.
            
            You MUST return ONLY a JSON object with this exact structure:
            {
                "status": "PASS" or "FAIL",
                "reason": "explanation",
                "retry": true or false
            }
            
            Do NOT include any other text or explanations.
            """,
            tools=self.tools
        )
        runner = InMemoryRunner(agent=agent)

        prompt = f"""
        Specification:
        {json.dumps(spec, indent=2)}
        
        Simulation Code:
        ```python
        {code}
        ```
        
        Please execute this code and verify the results.
        """
        
        session = None
        try:
            # Run the agent using run_debug (which handles session creation internally)
            # We will try to find the session afterwards
            response = await runner.run_debug(prompt)
            
            # Now try to find the session that was just used
            if hasattr(runner.session_service, 'sessions'):
                 # sessions is likely a dict {session_id: Session}
                 sessions_dict = runner.session_service.sessions
                 print(f"[DEBUG] Sessions dict keys: {list(sessions_dict.keys())}")
                 if sessions_dict:
                     # Get the most recent session
                     # Assuming keys are UUIDs, we can't sort by key.
                     # But we can check values.
                     # Let's just pick the last one added?
                     last_key = list(sessions_dict.keys())[-1]
                     session_val = sessions_dict[last_key]
                     print(f"[DEBUG] Session value type for key '{last_key}': {type(session_val)}")
                     if isinstance(session_val, dict):
                         print(f"[DEBUG] Nested keys: {list(session_val.keys())}")
                         # Maybe the nested dict is {session_id: Session}?
                         if session_val:
                             last_nested_key = list(session_val.keys())[-1]
                             nested_val = session_val[last_nested_key]
                             print(f"[DEBUG] Nested value type for key '{last_nested_key}': {type(nested_val)}")
                             
                             if isinstance(nested_val, dict):
                                 # Triple nested? {app_name: {user_id: {session_id: Session}}}
                                 print(f"[DEBUG] Triple nested keys: {list(nested_val.keys())}")
                                 if nested_val:
                                     last_inner_key = list(nested_val.keys())[-1]
                                     session = nested_val[last_inner_key]
                                     print(f"[DEBUG] Found session from triple nested dict: {getattr(session, 'id', 'UNKNOWN')}")
                             elif isinstance(nested_val, list):
                                 print(f"[DEBUG] Nested value is list of length: {len(nested_val)}")
                                 if len(nested_val) > 0:
                                     session = nested_val[-1]
                                     print(f"[DEBUG] Found session from list: {getattr(session, 'id', 'UNKNOWN')}")
                             else:
                                 session = nested_val
                                 print(f"[DEBUG] Found session from nested dict: {getattr(session, 'id', 'UNKNOWN')}")
                     else:
                         session = session_val
                         print(f"[DEBUG] Found session from service: {getattr(session, 'id', 'UNKNOWN')}")
                     
                     if session and hasattr(session, 'events'):
                        print(f"[DEBUG] Session events count: {len(session.events)}")
                     else:
                         session = session_val
                         print(f"[DEBUG] Found session from service: {getattr(session, 'id', 'UNKNOWN')}")
                     
                     if session and hasattr(session, 'events'):
                        print(f"[DEBUG] Session events count: {len(session.events)}")
            
        except Exception as e:
            print(f"[ERROR] Unexpected error in VerifierAgent: {e}")
            return {"status": "FAIL", "reason": f"Agent execution error: {e}", "retry": True}
        
        # Extract text response for JSON parsing
        text_response = ""
        # response is a list of Event objects
        if response and len(response) > 0:
            print(f"[DEBUG] Response length: {len(response)}")
            for i, event in enumerate(response[-3:]): # Print last 3 events
                print(f"[DEBUG] Event {len(response)-3+i} type: {type(event)}")
                if hasattr(event, 'content'):
                    print(f"[DEBUG] Event content parts: {len(event.content.parts) if event.content and event.content.parts else 0}")
                    if event.content and event.content.parts:
                        for part in event.content.parts:
                             print(f"[DEBUG] Part type: {type(part)}")
                             if hasattr(part, 'text'): print(f"[DEBUG] Part text (snippet): {part.text[:50] if part.text else 'None'}")
                             if hasattr(part, 'function_response'): print(f"[DEBUG] Part function_response: Yes")

            # Iterate backwards to find the last text response from model
            for event in reversed(response):
                if hasattr(event, 'content') and event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            # Check if it looks like the final JSON response
                            if "status" in part.text and ("PASS" in part.text or "FAIL" in part.text):
                                text_response = part.text
                                break
                    if text_response: break
            
            # Fallback: just take the last text part found
            if not text_response:
                 for event in reversed(response):
                    if hasattr(event, 'content') and event.content and event.content.parts:
                        for part in event.content.parts:
                            if hasattr(part, 'text') and part.text:
                                text_response = part.text
                                break
                        if text_response: break

            # last_event = response[-1]
            # if hasattr(last_event, 'content') and last_event.content and last_event.content.parts:
            #     for part in last_event.content.parts:
            #         if part.text:
            #             text_response += part.text
        
        # Extract logs from tool execution using the session history
        simulation_logs = ""
        
        # Check the session events directly - this should contain the full history including tool calls
        if session and hasattr(session, 'events'):
            turns_to_check = session.events
        else:
            turns_to_check = response

        try:
            for i, turn in enumerate(turns_to_check):
                # Skip prompt/user messages to avoid capturing code as logs
                if hasattr(turn, 'role') and turn.role == 'user':
                    continue
                
                # Check parts
                if hasattr(turn, 'content') and hasattr(turn.content, 'parts') and turn.content.parts:
                    for part in turn.content.parts:
                        # Skip FunctionCall (which contains the code in args)
                        if hasattr(part, 'function_call') and part.function_call:
                            continue

                        # Check Function Response (Tool Output)
                        if hasattr(part, 'function_response') and part.function_response:
                            resp = part.function_response
                            candidates = [
                                getattr(resp, 'response', None),
                                getattr(resp, 'content', None),
                                getattr(resp, 'result', None)
                            ]
                            
                            for candidate in candidates:
                                if candidate:
                                    cand_str = str(candidate)
                                    # Extract lines starting with [SIM]
                                    import re
                                    matches = re.findall(r'(\[SIM\].*?)(?=\\n|\n|$)', cand_str)
                                    if matches:
                                        for match in matches:
                                            if match not in simulation_logs:
                                                simulation_logs += match + "\n"
                                    
                                    # Also check for errors
                                    if "ERRORS:" in cand_str or "Traceback" in cand_str:
                                        simulation_logs += f"\n[SYSTEM] Simulation Execution Errors:\n{cand_str}\n"

                        # Check Text Content (Model Response or Tool Output as text)
                        # Note: We should be careful not to extract logs from model's reasoning if it quotes the code.
                        # But usually model response is analysis.
                        # DISABLED to prevent capturing source code from model reasoning
                        # if hasattr(part, 'text') and part.text:
                        #     if "[SIM]" in part.text:
                        #         import re
                        #         matches = re.findall(r'(\[SIM\].*?)(?=\\n|\n|$)', part.text)
                        #         if matches:
                        #             for match in matches:
                        #                 if match not in simulation_logs:
                        #                     simulation_logs += match + "\n"

        except Exception as e:
            print(f"[WARNING] Could not extract logs: {e}")
            simulation_logs = f"Error extracting logs: {e}"

        # REMOVED DANGEROUS FALLBACK LOOP that was capturing source code from FunctionCall
        
        # If no logs found, check for errors in the response explicitly to provide better context
        if not simulation_logs:
             for turn in turns_to_check:
                if hasattr(turn, 'role') and turn.role == 'user': continue
                if hasattr(turn, 'content') and hasattr(turn.content, 'parts') and turn.content.parts:
                    for part in turn.content.parts:
                        if hasattr(part, 'function_response') and part.function_response:
                            resp = part.function_response
                            candidates = [
                                getattr(resp, 'response', None),
                                getattr(resp, 'content', None),
                                getattr(resp, 'result', None)
                            ]
                            for candidate in candidates:
                                if candidate:
                                    cand_str = str(candidate)
                                    if "ERRORS:" in cand_str or "Traceback" in cand_str:
                                        simulation_logs += f"\n[SYSTEM] Simulation Execution Errors:\n{cand_str}\n"

        if not text_response:
            # If empty response, construct a JSON based on logs/errors
            if "Simulation Execution Errors" in simulation_logs:
                return {"status": "FAIL", "reason": "Simulation Execution Errors", "retry": True, "logs": simulation_logs}
            elif not simulation_logs:
                return {"status": "FAIL", "reason": "No simulation logs produced and no model response", "retry": True}
            else:
                # Logs exist but model didn't verify? Assume fail or retry
                return {"status": "FAIL", "reason": "Empty response from Verifier Agent", "retry": True, "logs": simulation_logs}

        try:
            # Clean up potential markdown
            if "```json" in text_response:
                import re
                match = re.search(r'```json\s*(\{.*?\})\s*```', text_response, re.DOTALL)
                if match:
                    text_response = match.group(1)
                else:
                    text_response = text_response.replace("```json", "").replace("```", "")
            
            # Try to find JSON block with regex if direct parse fails or just in case
            import re
            match = re.search(r'\{.*\}', text_response, re.DOTALL)
            result_json = {}
            if match:
                result_json = json.loads(match.group(0))
            else:
                result_json = json.loads(text_response.strip())
            
            # Attach logs to the result
            result_json['logs'] = simulation_logs if simulation_logs else "No logs captured from tool execution."
            return result_json

        except Exception as e:
            print(f"Error parsing JSON from Verifier Agent: {e}")
            print(f"Raw response: {text_response}")
            return {"status": "FAIL", "reason": f"JSON parsing error: {e}", "retry": True, "logs": simulation_logs}

