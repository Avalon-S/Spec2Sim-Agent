from mcp.server.fastmcp import FastMCP
import io
import contextlib
import traceback
import json
import html

# Create an MCP server
mcp = FastMCP("VeriSpec Simulation Server")

@mcp.tool()
def execute_simulation_code(code_str: str) -> str:
    """
    Safely executes SimPy simulation code and returns the logs.
    
    Args:
        code_str: The Python code to execute.
        
    Returns:
        A string containing the standard output (logs) and standard error (if any).
    """
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    print(f"Executing code via MCP...")

    # DEBUG: Save code to file to inspect what is being executed
    with open("debug_last_code.py", "w", encoding="utf-8") as f:
        f.write(code_str)

    try:
        # Unescape HTML entities in case the code contains escaped characters like \u003e for >
        code_str = html.unescape(code_str)
        
        # In a real production environment, this should be sandboxed (e.g., Docker, gVisor)
        # For this lite version, we use exec() with redirected I/O
        with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
            # Create a fresh global namespace for execution to avoid pollution
            # CRITICAL: Set __name__ to "__main__" so that if __name__ == "__main__": blocks execute
            exec_globals = {"__name__": "__main__"}
            exec(code_str, exec_globals)
    except Exception:
        traceback.print_exc(file=stderr_capture)

    output = stdout_capture.getvalue()
    errors = stderr_capture.getvalue()
    
    result = ""
    if output:
        result += f"LOGS:\n{output}\n"
    if errors:
        result += f"\nERRORS:\n{errors}"
        
    if not result:
        result = "No output produced."
        
    return result

@mcp.tool()
def generate_mermaid_diagram(spec: dict) -> str:
    """
    Convert spec into Mermaid stateDiagram-v2.
    
    Args:
        spec: The specification dictionary containing 'transitions' and 'states'.
        
    Returns:
        A string containing the Mermaid diagram definition.
    """
    lines = ["stateDiagram-v2"]
    
    # Add transitions
    if "transitions" in spec:
        for t in spec["transitions"]:
            # Format: StateA --> StateB : Condition
            line = f"    {t['from']} --> {t['to']}"
            if "condition" in t and t["condition"]:
                line += f" : {t['condition']}"
            lines.append(line)
            
    # Add states (if needed to ensure they appear, though transitions usually cover it)
    if "states" in spec:
        for s in spec["states"]:
            # Just listing states if they have specific descriptions or notes could be added here
            pass

    return "\n".join(lines)

if __name__ == "__main__":
    mcp.run()
