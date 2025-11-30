import os
import asyncio
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.genai import types
from google.genai.errors import ServerError, ClientError
from core import config

class ArchitectAgent:
    def __init__(self):
        pass

    async def generate_simulation_code(self, spec: dict, feedback: str = None) -> str:
        # Initialize agent and runner inside the method to ensure they are tied to the current asyncio loop
        agent = LlmAgent(
            name='architect_agent',
            model=Gemini(
                model=config.MODEL_NAME, 
                generation_config=config.GENERATION_CONFIG,
                retry_options=config.RETRY_OPTIONS
            ),
            description="Generates SimPy simulation code from specifications.",
            instruction="""
            You are an expert software architect. Generate a Python simulation using SimPy based on the provided specification.
            
            Requirements:
            1. Use `simpy` for the simulation environment.
            2. Implement a StateMachine class (no external dependency, hand-code it).
            3. **Structured Logging**: You MUST print logs in the following EXACT format (replace <...> with actual values):
               - Start: `[SIM] Starting simulation`
               - State Entry: `[SIM][t=<env.now>] ENTER state=<state_name>`
               - Wait: `[SIM][t=<env.now>] WAIT <duration>s for <event_name>`
               - Transition: `[SIM][t=<env.now>] TRANSITION <from_state> -> <to_state> (reason=<condition>)`
               - End: `[SIM][t=<env.now>] END state=<final_state>`
               - **CRITICAL**: You MUST log ALL state changes using the `TRANSITION` format.
            4. Implement timeouts using `yield env.timeout(x)`.
            5. **Time & Units**:
                - **SimPy Time**: Treat SimPy time as **seconds**.
                - **Unit Conversion**: If the spec defines values in milliseconds (e.g., `2000ms`), you MUST convert them to seconds (e.g., `2000/1000 = 2`) for `env.timeout()`.
                - If a transition condition contains a duration (e.g., "30s elapsed") and the corresponding parameter is NOT in `self.constraints`, you MUST parse the integer value directly from the condition string in the generated code.
                - **Missing Constraints**: If a constraint value is `None` or missing, you MUST assign a sensible default value in the generated code to ensure the simulation runs.
            6. **Scenario Coverage**:
                - **CASE A: Input-Driven or Hybrid Systems** (e.g., transitions depend on external values):
                  - Implement a `test_scenarios(env, state_machine)` process that drives the simulation.
                  - Inside `test_scenarios`, write a linear sequence of events using `yield env.timeout(x)` and setting inputs.
                - **CASE B: Time-Driven Systems** (e.g., Traffic Light, transitions depend on `elapsed` time):
                  - Do NOT use an input loop.
                  - Simply run the state machine for a fixed duration (e.g., `env.run(until=120)`).
                  - **CRITICAL**: You MUST use the specific durations defined in the constraints or transition conditions (e.g., `yield env.timeout(30)`).
            7. **Execution & Testing**:
               - Define a function `run_simulation()` that sets up the environment and runs it.
               - **State Machine Structure**:
                 - Use a single `run()` process that loops and checks `self.current_state`.
                 - **CRITICAL**: Do NOT use `env.process()` for individual state methods. Just call them as **generators** using `yield from self.idle()`.
                 - Example:
                   ```python
                   def run(self):
                       while True:
                           if self.current_state == 'Idle':
                               yield from self.idle()
                           elif self.current_state == 'Brew':
                               yield from self.brew()
                   ```
                 - Ensure ALL state methods are generators (have at least one `yield`).
                 - **CRITICAL**: If a state method has an immediate transition and no natural wait, you MUST add `yield env.timeout(0.001)` to make it a generator. NEVER use `yield env.timeout(0)` as it causes infinite loops.
               - **Main Execution**:
                 - In `run_simulation`:
                   1. Create `env` and `state_machine`.
                   2. `env.process(state_machine.run())`
                   3. (Optional) `env.process(test_scenarios(env, state_machine))` for input-driven systems
                   4. `env.run(until=X)`
                   5. `print("[SIM] END simulation")`
            8. Return ONLY the Python code.
            """
        )
        runner = InMemoryRunner(agent=agent)

        try:
            # Run the runner directly since we are now in an async method
            # Native retry logic in Gemini model will handle 503/429 errors
            prompt = f"Specification:\n{spec}"
            if feedback:
                prompt += f"\n\nFEEDBACK FROM PREVIOUS ATTEMPT (FIX THESE ERRORS):\n{feedback}"
            
            response = await runner.run_debug(prompt)
        except Exception as e:
            print(f"[ERROR] Unexpected error in ArchitectAgent: {e}")
            return ""
        
        # response is a list of Turn objects
        text_response = ""
        if response and len(response) > 0:
            last_turn = response[-1]
            if hasattr(last_turn, 'content') and last_turn.content and last_turn.content.parts:
                text_response = last_turn.content.parts[0].text
        
        if not text_response:
            text_response = str(response)
        
        # Clean up markdown
        if "```python" in text_response:
            import re
            match = re.search(r'```python\s*(.*?)\s*```', text_response, re.DOTALL)
            if match:
                text_response = match.group(1)
            else:
                text_response = text_response.replace("```python", "").replace("```", "")
        elif "```" in text_response:
             text_response = text_response.replace("```", "")
            
        return text_response.strip()
