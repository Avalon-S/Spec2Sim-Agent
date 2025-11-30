import streamlit as st
import time
import os
import glob
from core.orchestrator import run_pipeline

st.set_page_config(page_title="Spec2Sim-Agent", layout="wide")

st.title("Spec2Sim-Agent: Agentic Verification")

# Function to load specs from files
@st.cache_data
def load_specs_from_files():
    """Load all spec files from the specs/ directory."""
    specs = {}
    specs_dir = "specs"
    
    # Define preferred order for display
    preferred_order = [
        "traffic_light.txt",
        "bms_precharge.txt",
        "elevator.txt"
    ]
    
    if os.path.exists(specs_dir):
        # Find all .txt files in the specs directory
        spec_files = glob.glob(os.path.join(specs_dir, "*.txt"))
        
        # Sort files according to preferred order
        def sort_key(filepath):
            filename = os.path.basename(filepath)
            if filename in preferred_order:
                return preferred_order.index(filename)
            else:
                return len(preferred_order)  # Put unknown files at the end
        
        spec_files = sorted(spec_files, key=sort_key)
        
        for spec_file in spec_files:
            # Get the filename without extension for the display name
            filename = os.path.basename(spec_file)
            # Create a nice display name from the filename
            display_name = filename.replace(".txt", "").replace("_", " ").title()
            
            # Read the file content
            try:
                with open(spec_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:  # Only add non-empty files
                        specs[display_name] = content
            except Exception as e:
                st.sidebar.warning(f"Could not load {filename}: {e}")
    
    # Add a custom option for user input at the end
    specs["[Custom Input]"] = ""
    
    return specs

# Sidebar for inputs
with st.sidebar:
    st.header("System Specification")
    
    # Load specs from files
    examples = load_specs_from_files()
    
    if not examples or len(examples) == 1:  # Only custom input
        st.warning("No spec files found in specs/ directory")
        spec_text = st.text_area("Enter Spec", value="", height=300)
    else:
        selected_example = st.selectbox("Load Example", list(examples.keys()))
        
        # Show file path info for loaded specs
        if selected_example != "[Custom Input]":
            spec_filename = selected_example.lower().replace(" ", "_") + ".txt"
            st.caption(f"Loaded from: `specs/{spec_filename}`")
        
        # If custom input is selected, start with empty text
        initial_value = examples[selected_example] if selected_example != "[Custom Input]" else ""
        spec_text = st.text_area("Enter Spec", value=initial_value, height=300)
    
    run_btn = st.button("Run Verification", type="primary")

# Main area
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Agent Execution Log")
    # Use a scrollable container with fixed height
    with st.container(height=600):
        log_container = st.empty()
    logs = []

    def log_callback(message):
        logs.append(message)
        # Update the log container with the latest logs
        log_container.code("\n".join(logs), language="text")
        # Small delay to visualize the "thinking" process
        time.sleep(0.05)

    if run_btn:
        import asyncio
        with st.spinner("Agents are working (Analyst -> Architect -> Verifier)..."):
            # Create a new event loop for this thread if needed
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(run_pipeline(spec_text, log_callback=log_callback))
            except Exception as e:
                st.error(f"Execution Error: {e}")
                result = None
            finally:
                loop.close()
            
            if result:
                st.session_state['result'] = result
                if result.get("status") == "PASS":
                    st.success("Verification Passed!")
                else:
                    st.error("Verification Failed.")
            else:
                st.error("Pipeline execution failed.")

with col2:
    st.subheader("Results")
    if 'result' in st.session_state:
        result = st.session_state['result']
        
        tab1, tab2, tab3 = st.tabs(["Diagram", "Simulation Code", "Execution Logs"])
        
        with tab1:
            if result.get("mermaid"):
                st.markdown(f"```mermaid\n{result['mermaid']}\n```")
            else:
                st.info("No diagram generated.")
                
        with tab2:
            with st.container(height=600):
                if result.get("code"):
                    st.code(result['code'], language="python")
                else:
                    st.info("No code generated.")
                
        with tab3:
            with st.container(height=600):
                if result.get("logs"):
                    st.code(result['logs'], language="text")
                else:
                    st.info("No logs available.")
