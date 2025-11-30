"""
Spec2Sim-Agent Deployment Wrapper for Vertex AI Agent Engine (Simplified)

This version removes the immediate orchestrator import to avoid build issues.
The agent will provide a simpler interface for demonstration.
"""
import os
from google.adk.agents import Agent
import vertexai

# Initialize Vertex AI
vertexai.init(
    project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
    location=os.environ.get("GOOGLE_CLOUD_LOCATION", "global"),
)

def analyze_specification(spec_text: str) -> dict:
    """
    Analyze a hardware specification and extract key information.
    
    This is a simplified version that demonstrates the agent's capability
    without running the full pipeline (which requires MCP server).
    
    Args:
        spec_text: Natural language hardware specification
        
    Returns:
        dict: Analysis results
    """
    try:
        return {
            "status": "success",
            "message": "Specification received. The full Spec2Sim-Agent pipeline includes: 1) Analyst Agent (extracts state machine), 2) Architect Agent (generates SimPy code), 3) Verifier Agent (validates simulation).",
            "spec_preview": spec_text[:200] + "..." if len(spec_text) > 200 else spec_text,
            "note": "This is a deployment demonstration. For full functionality with code generation, please run the local version."
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": f"Failed to process specification: {str(e)}"
        }

# Define the deployment agent
root_agent = Agent(
    name="spec2sim_agent",
    model="gemini-2.0-flash-001",
    description="Demonstrates Spec2Sim-Agent: converts hardware specifications into verified SimPy simulation code using a multi-agent system.",
    instruction="""
    You are Spec2Sim-Agent, an AI system that converts natural language hardware 
    specifications into verified simulation code.
    
    This is a deployment demonstration. When users provide a hardware specification:
    1. Use the analyze_specification tool to receive and acknowledge the specification
    2. Explain that the full system runs locally with three agents:
       - Analyst Agent: Extracts state machines from natural language
       - Architect Agent: Generates SimPy simulation code  
       - Verifier Agent: Validates simulations via MCP server
    3. Provide helpful information about the specification
    
    Supported specifications include:
    - State machines (traffic lights, elevators, control systems)
    - Hardware protocols (CAN, I2C, SPI)
    - Embedded systems (BMS, motor controllers)
    
    Be helpful and explain the Spec2Sim-Agent system clearly.
    """,
    tools=[analyze_specification]
)
