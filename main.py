import json
import zipfile
import sys

# Dictionary mapping internal Scratch opcodes to clean pseudocode formats
OPCODE_MAP = {
    # Events
    "event_whenflagclicked": "when 🚩 clicked",
    "event_whenkeypressed": "when key [{0}] pressed",
    "event_whenthisspriteclicked": "when this sprite clicked",
    "control_start_as_clone": "when I start as a clone",
    # Motion
    "motion_movesteps": "move ({0}) steps",
    "motion_gotoxy": "go to x: ({0}) y: ({1})",
    "motion_changeyby": "change y by ({0})",
    "motion_pointindirection": "point in direction ({0})",
    # Looks
    "looks_hide": "hide",
    "looks_show": "show",
    "looks_switchcostumeto": "switch costume to [{0}]",
    "looks_nextcostume": "next costume",
    "looks_goforwardbackwardlayers": "go {0} {1} layers",
    # Variables
    "data_setvariableto": "set [{0}] to ({1})",
    "data_changevariableby": "change [{0}] by ({1})",
    # Control
    "control_repeat": "repeat ({0})",
    "control_forever": "forever",
    "control_if": "if <{0}> then",
    "control_if_else": "if <{0}> then",
    "control_create_clone_of": "create clone of [{0}]",
    # Operators
    "operator_round": "round({0})",
    "operator_multiply": "({0} * {1})",
    "operator_or": "({0} or {1})",
    # Sensing
    "sensing_keypressed": "key [{0}] pressed?",
    "procedures_call": "call custom block",
    "procedures_definition": "define custom block",
}


def clean_value(val):
    """Unwraps redundant menu blocks like sensing_keyoptions(a) -> a."""
    if val.startswith("sensing_keyoptions(") and val.endswith(")"):
        return val[19:-1]
    if val.startswith("control_create_clone_of_menu(") and val.endswith(")"):
        inner = val[29:-1]
        return "myself" if inner == "_myself_" else inner
    if val == "procedures_prototype":
        return "My Block"
    return val


def parse_block(block_id, blocks):
    if not block_id or block_id not in blocks:
        return ""

    block = blocks[block_id]
    if isinstance(block, list):
        return str(block[1]) if len(block) > 1 else ""

    opcode = block.get("opcode", "")
    inputs = block.get("inputs", {})
    fields = block.get("fields", {})
    next_block = block.get("next")

    # Handle dropdown fields directly
    field_args = [str(v[0]) for v in fields.values()]

    input_args = []
    sub_stacks = []

    # Sort inputs so SUBSTACK2 (else) comes after SUBSTACK (if)
    for name, val in sorted(inputs.items()):
        if isinstance(val, list) and len(val) > 1:
            target = val[1]
            if isinstance(target, str):
                parsed = parse_block(target, blocks)
                if "SUBSTACK" in name:
                    sub_stacks.append((name, parsed))
                else:
                    input_args.append(clean_value(parsed))
            elif isinstance(target, list):
                input_args.append(clean_value(str(target[1])))

    args = field_args + input_args

    # Format using OPCODE_MAP if available
    if opcode in OPCODE_MAP:
        template = OPCODE_MAP[opcode]
        try:
            text = template.format(*args)
        except IndexError:
            text = f"{opcode}({', '.join(args)})"
    else:
        text = f"{opcode}({', '.join(args)})"

    # Control block structures (if, repeat, forever, if-else)
    if sub_stacks:
        for stack_name, stack_code in sub_stacks:
            indented = "\n    ".join("\n".join(stack_code.split("\n")).split("\n"))
            if stack_name == "SUBSTACK2":
                text += f"\nelse {{\n    {indented}\n}}"
            else:
                text += f" {{\n    {indented}\n}}"

    if next_block:
        text += "\n" + parse_block(next_block, blocks)

    return text


def sb3_to_text(sb3_file_path):
    with zipfile.ZipFile(sb3_file_path, "r") as archive:
        with archive.open("project.json") as f:
            data = json.load(f)

    out = []
    for target in data.get("targets", []):
        name = target.get("name", "Unnamed")
        target_type = "Stage" if target.get("isStage", False) else f"Sprite: {name}"
        out.append(f"=== {target_type} ===")

        vars_list = [v[0] for v in target.get("variables", {}).values()]
        if vars_list:
            out.append(f"Variables: {', '.join(vars_list)}")

        blocks = target.get("blocks", {})
        top_blocks = [
            b_id
            for b_id, b in blocks.items()
            if isinstance(b, dict) and b.get("topLevel", False)
        ]

        if not top_blocks:
            out.append("  (No code scripts found)\n")
            continue

        for script_id in top_blocks:
            out.append("--- Script ---")
            out.append(parse_block(script_id, blocks))
            out.append("")

        out.append("\n")

    return "\n".join(out)

args = sys.argv[1:]
filename = sys.argv[1]

if "-o" in args:
    print(sb3_to_text(f"{filename}"))
else:
    with open(f"{filename}.txt", "w", encoding='utf-8') as f:
        f.write(sb3_to_text(f"{filename}"))   

