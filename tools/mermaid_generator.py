def spec_to_mermaid(spec: dict) -> str:
    """
    Convert spec into Mermaid stateDiagram-v2.
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
