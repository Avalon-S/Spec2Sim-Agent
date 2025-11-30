import os
import sys

# Add parent directory to path to import orchestrator
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.orchestrator import run_pipeline

def main():
    spec_path = os.path.join("specs", "traffic_light.txt")
    with open(spec_path, "r") as f:
        text = f.read()
        
    print(f"Loading Spec: {spec_path}")
    import asyncio
    result = asyncio.run(run_pipeline(text, output_name="demo_traffic_light"))
    
    # Exit with proper code based on result
    if result and result.get("status") == "PASS":
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
