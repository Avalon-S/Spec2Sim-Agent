# Model Configuration
# NOTE: This project uses gemini-2.5-flash-lite exclusively
MODEL_NAME = "gemini-2.5-flash-lite"

from google.genai import types

GENERATION_CONFIG = types.GenerateContentConfig(
    temperature=0.1,  # Low but not zero - balances consistency with diversity
    max_output_tokens=8192,
)

# JSON Generation Config for Verifier Agent
# Enforces structured JSON output with strict schema
JSON_GENERATION_CONFIG = types.GenerationConfig(
    temperature=0.1,  # Low but not zero - balances consistency with diversity
    max_output_tokens=2048,
    top_p=0.95,
    top_k=20,
    response_mime_type="application/json",
    response_schema={
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["PASS", "FAIL"]},
            "reason": {"type": "string"},
            "retry": {"type": "boolean"}
        },
        "required": ["status", "reason", "retry"]
    }
)

# Retry Configuration (Native ADK/GenAI Style)
RETRY_OPTIONS = types.HttpRetryOptions(
    attempts=10, # Maximum retry attempts
    exp_base=2,  # Delay multiplier (tutorial uses 7, but 2 is standard exponential)
    initial_delay=2, # Initial delay in seconds
    http_status_codes=[429, 500, 503, 504] # Retry on these errors
)

# Timeout Configuration
REQUEST_TIMEOUT = 60  # seconds
MCP_TIMEOUT = 20 # seconds for MCP tool execution
