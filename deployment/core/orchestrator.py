"""
Spec2Sim-Agent Orchestrator

This module implements the core multi-agent pipeline using a sequential loop architecture.
It coordinates the interaction between three specialized agents:
1. Analyst: Understands the requirements.
2. Architect: Builds the solution.
3. Verifier: Ensures quality and correctness.

This design demonstrates the "Loop Agents" pattern where the system iterates until
a verification condition is met or max retries are exceeded.
"""

import os
import sys
import inspect
from dotenv import load_dotenv
from agents.analyst_agent import AnalystAgent
from agents.architect_agent import ArchitectAgent
from agents.verifier_agent import VerifierAgent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
from core import config

# Load environment variables
load_dotenv()

class TeeLogger:
    """
    A helper class to write output to both the terminal and a log file simultaneously.
    This ensures we capture all simulation artifacts for review.
    """
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "w", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()  # Ensure immediate write

    def flush(self):
        self.terminal.flush()
        self.log.flush()

    def close(self):
        self.log.close()

async def run_pipeline(text: str, output_name: str = None, log_callback=print):
    # Setup logging if output_name is provided
    original_stdout = sys.stdout
    tee_logger = None
    
    if output_name:
        output_dir = "outputs"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        output_file = os.path.join(output_dir, f"{output_name}.txt")
        tee_logger = TeeLogger(output_file)
        sys.stdout = tee_logger
        log_callback(f"Logging output to: {output_file}")

    try:
        log_callback("--- Starting Spec2Sim-Agent Pipeline ---")
        
        # Initialize Agents with MCP
        # Initialize Agents
        # Resolve server script path
        server_script = os.path.join("servers", "simulation_server.py")
        if not os.path.exists(server_script):
                # Fallback for different CWD
                server_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "servers", "simulation_server.py"))

        analyst = AnalystAgent()
        architect = ArchitectAgent()
            
        # 1. Analyst -> JSON Spec
        log_callback("\n[1] Analyst Agent: Extracting Spec...")
        spec = await analyst.extract_spec(text)
        log_callback(f"    Spec: {spec}")
        
        # Generate Mermaid Diagram locally
        log_callback("\n[1.5] Generating Mermaid Diagram...")
        mermaid_code = "stateDiagram-v2\n"
        try:
            if "transitions" in spec:
                for t in spec["transitions"]:
                    # Format: StateA --> StateB : Condition
                    line = f"    {t['from']} --> {t['to']}"
                    if "condition" in t and t["condition"]:
                        line += f" : {t['condition']}"
                    mermaid_code += line + "\n"
        except Exception as e:
            mermaid_code = f"Error generating diagram: {e}"
            log_callback(f"    Error generating diagram: {e}") 
            
        attempts = 0
        max_retries = 10
        feedback = None
        
        while attempts <= max_retries:
            simulation_mcp = None
            try:
                # Initialize MCP Toolset for each attempt to ensure fresh state
                simulation_mcp = McpToolset(
                    connection_params=StdioConnectionParams(
                        server_params=StdioServerParameters(
                            command=sys.executable, 
                            args=[server_script],
                        ),
                        timeout=config.MCP_TIMEOUT
                    )
                )

                log_callback(f"\n[2] Architect Agent: Generating Code (Attempt {attempts + 1})...")
                # 2. Architect -> Code
                code = await architect.generate_simulation_code(spec, feedback=feedback)
                log_callback("    Code Generated.")
                log_callback(f"    --- Generated Code ---\n{code}\n    ----------------------")
                
                # 3. Verifier -> Execute & Verify (via MCP)
                log_callback("\n[3] Verifier Agent: Executing & Verifying via MCP...")
                
                # Use the existing MCP toolset
                verifier = VerifierAgent(tools=[simulation_mcp])
                # Note: We pass 'code' directly. The VerifierAgent will call the MCP tool to execute it.
                verification = await verifier.verify(spec, code)
                log_callback(f"    Verification: {verification}")
                
                if verification.get("status") == "PASS":
                    log_callback("\nSUCCESS: Model Verified.")
                    return {
                        "status": "PASS",
                        "spec": spec,
                        "mermaid": mermaid_code,
                        "code": code,
                        "logs": verification.get("logs", "No logs returned by Verifier")
                    }
                
                # Update feedback for next attempt
                feedback = f"Verification Failed: {verification.get('reason')}\nLogs/Errors:\n{verification.get('logs')}"
                
                if not verification.get("retry", False):
                    log_callback("\nFAILURE: Verification failed (No Retry).")
                    break
                    
                attempts += 1
                log_callback("    Retrying...")

            except Exception as e:
                log_callback(f"Error during attempt {attempts + 1}: {e}")
                feedback = f"System Error during attempt {attempts + 1}: {e}"
                attempts += 1
            finally:
                # Close MCP Toolset for this attempt
                if simulation_mcp:
                    try:
                        if inspect.iscoroutinefunction(simulation_mcp.close):
                            await simulation_mcp.close()
                        else:
                            simulation_mcp.close()
                    except Exception as e:
                        pass

        log_callback("\nFAILURE: Max retries reached or unrecoverable error.")
        return {
            "status": "FAIL",
            "spec": spec,
            "mermaid": mermaid_code,
            "code": code if 'code' in locals() else "",
            "logs": ""
        }

    except Exception as e:
        log_callback(f"Pipeline Error: {e}")
        import traceback
        traceback.print_exc()
        return None

    finally:
        # Restore stdout
        if tee_logger:
            sys.stdout = original_stdout
            tee_logger.close()
