import json
import zipfile

def parse_block(block_id, blocks):
    """Recursively converts a block and its inputs/children to text."""
    if not block_id or block_id not in blocks:
        return ""

    block = blocks[block_id]
    
    # Handle primitive values or simple inputs that aren't full blocks
    if isinstance(block, list):
        return str(block[1]) if len(block) > 1 else ""

    opcode = block.get("opcode", "")
    inputs = block.get("inputs", {})
    fields = block.get("fields", {})
    next_block = block.get("next")

    # Format fields (e.g., variable names, dropdown selections)
    field_str = " ".join([f"{v[0]}" for k, v in fields.items()])
    
    # Process inputs (e.g., math, nested expressions, block stacks)
    input_texts = []
    sub_stacks = []

    for name, val in inputs.items():
        # val structure: [shadow_type, block_id_or_primitive]
        if isinstance(val, list) and len(val) > 1:
            target = val[1]
            if isinstance(target, str):
                parsed = parse_block(target, blocks)
                if "SUBSTACK" in name:
                    sub_stacks.append(parsed)
                else:
                    input_texts.append(parsed)
            elif isinstance(target, list):  # Primitive array like [10, "hello"]
                input_texts.append(str(target[1]))

    # Construct block text representation
    args = ", ".join(filter(None, [field_str] + input_texts))
    text = f"{opcode}({args})" if args else opcode

    # Format control structures (if statements, loops)
    if sub_stacks:
        body = "\n    ".join("\n".join(sub_stacks).split("\n"))
        text += f" {{\n    {body}\n}}"

    # Chain to the next sequential block
    if next_block:
        text += "\n" + parse_block(next_block, blocks)

    return text

def sb3_to_text(sb3_file_path):
    """Extracts project.json from an .sb3 file and turns scripts into pseudocode."""
    with zipfile.ZipFile(sb3_file_path, 'r') as archive:
        with archive.open('project.json') as f:
            data = json.load(f)

    out = []
    
    for target in data.get("targets", []):
        name = target.get("name", "Unnamed")
        is_stage = target.get("isStage", False)
        target_type = "Stage" if is_stage else f"Sprite: {name}"
        
        out.append(f"=== {target_type} ===")

        # Variables & Lists
        vars_list = [v[0] for v in target.get("variables", {}).values()]
        if vars_list:
            out.append(f"Variables: {', '.join(vars_list)}")

        blocks = target.get("blocks", {})
        
        # Top-level blocks represent the start of distinct scripts (e.g., when green flag clicked)
        top_blocks = [
            b_id for b_id, b in blocks.items() 
            if isinstance(b, dict) and b.get("topLevel", False)
        ]

        if not top_blocks:
            out.append("  (No code scripts found)\n")
            continue

        for script_id in top_blocks:
            script_text = parse_block(script_id, blocks)
            out.append("--- Script ---")
            out.append(script_text)
            out.append("")

        out.append("\n")

    return "\n".join(out)

# --- Usage Example ---
print(sb3_to_text("Car Thing2.sb3"))