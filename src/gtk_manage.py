import os
import shutil
from pathlib import Path

GTK3_FOLDERS = ["gtk3", "gtk-3.0"]

GTK_CSS_FILES = [
    "gtk.css",
    "gtk-dark.css"
]

def get_gtk_css_paths(theme_dir):
    results = []

    for folder in GTK3_FOLDERS:
        folder_path = os.path.join(theme_dir, folder)

        if not os.path.isdir(folder_path):
            continue

        for filename in GTK_CSS_FILES:
            path = os.path.join(folder_path, filename)

            if os.path.isfile(path):
                results.append(path)

    return results

def _split_selectors(selector_text):
    selectors = []
    current = ""
    depth = 0
    string_char = None
    previous_char = ""

    for char in selector_text:
        if string_char:
            current += char
            if char == string_char and previous_char != "\\":
                string_char = None
        elif char in ('"', "'"):
            current += char
            string_char = char
        elif char == "(":
            current += char
            depth += 1
        elif char == ")":
            current += char
            depth = max(depth - 1, 0)
        elif char == "," and depth == 0:
            selectors.append(current.strip())
            current = ""
        else:
            current += char

        previous_char = char

    if current.strip():
        selectors.append(current.strip())

    return [selector for selector in selectors if selector]


def _find_matching_brace(text, start_index):
    depth = 0
    for index in range(start_index, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    return -1


def parse_gtk_css(css_text):
    if css_text is None:
        return None

    normalized = css_text.replace("\r\n", "\n").replace("\r", "\n")
    blocks = []
    pos = 0
    length = len(normalized)
    preamble = ""

    # Collect any @ directives at the start of the file
    while pos < length:
        # Look for @ directives
        at_pos = normalized.find("@", pos)
        if at_pos == -1 or at_pos > pos:
            break
        
        # Check if it's a directive (ends with ;)
        semicolon_pos = normalized.find(";", at_pos)
        if semicolon_pos == -1:
            break
        
        next_at = normalized.find("@", semicolon_pos + 1)
        next_brace = normalized.find("{", semicolon_pos + 1)
        
        # If there's another @ or a { before the next newline, this is a preamble directive
        if (next_at > 0 and next_at < next_brace) or (next_brace == -1 and next_at > 0):
            # Check if it's on a line by itself or at the start
            line_start = normalized.rfind("\n", 0, at_pos)
            if line_start == -1:
                line_start = 0
            else:
                line_start += 1
            
            if normalized[line_start:at_pos].strip() == "":
                # It's a preamble directive
                preamble += normalized[pos:semicolon_pos + 1] + "\n"
                pos = semicolon_pos + 1
                continue
        
        break

    # Remove preamble from processing and add blank line after
    if preamble:
        normalized = preamble + "\n" + normalized[pos:]
        pos = len(preamble) + 1

    while pos < len(normalized):
        # Find the next opening brace
        open_brace = normalized.find("{", pos)
        if open_brace == -1:
            break

        # Extract everything from current pos to {
        between = normalized[pos:open_brace]

        # Split by lines and process from the end (near the {)
        lines = between.split("\n")
        
        # Collect non-empty lines from the end for selector
        selector_lines = []
        prefix_end_idx = len(lines)
        
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip():
                selector_lines.insert(0, lines[i])
            else:
                # Found empty line, this marks the end of selector
                prefix_end_idx = i + 1
                break
        else:
            # No empty line found, all non-empty lines are selectors
            prefix_end_idx = 0

        # Build prefix (lines before selector)
        prefix = "\n".join(lines[:prefix_end_idx])
        if prefix and not prefix.endswith("\n"):
            prefix += "\n"

        # Build selector
        raw_selector = " ".join([l.strip() for l in selector_lines if l.strip()])

        if not raw_selector:
            pos = open_brace + 1
            continue

        # Find matching closing brace
        close_brace = _find_matching_brace(normalized, open_brace)
        if close_brace == -1:
            break

        declarations = normalized[open_brace + 1 : close_brace]

        # Split multi-selectors
        selectors = _split_selectors(raw_selector)

        for selector in selectors:
            blocks.append(
                {
                    "prefix": prefix,
                    "selector": selector.strip(),
                    "declarations": declarations,
                }
            )
            prefix = ""

        pos = close_brace + 1

    suffix = normalized[pos:]
    return {"blocks": blocks, "suffix": suffix, "preamble": preamble}


def normalize_gtk_css(css_text):
    """Normalize GTK CSS by:
    - Separating multi-selectors into individual blocks
    - Removing unnecessary spaces (e.g., "button: hover" -> "button:hover")
    - Merging blocks with the same selector
    - Removing duplicate properties (keeping the last one)
    - Sorting selectors alphabetically (preserves rendering due to CSS cascade rules)
    """
    if css_text is None:
        return ""

    parsed = parse_gtk_css(css_text)
    if not parsed:
        return ""

    # Step 1: Collect all blocks by selector and merge them
    blocks_by_selector = {}

    for block in parsed.get("blocks", []):
        selector = block.get("selector", "").strip()
        declarations = block.get("declarations", "").strip()

        if not selector:
            continue

        # Clean up selector: remove extra spaces before and after colons
        selector = selector.replace(" :", ":").replace(": ", ":")

        # Parse declarations and remove duplicates (keep last)
        decl_dict = {}
        for line in declarations.splitlines():
            line = line.strip()
            if not line or line.startswith("/*"):
                continue
            if ":" in line:
                prop = line.split(":", 1)[0].strip()
                decl_dict[prop] = line

        # Merge with existing selector or add new
        if selector not in blocks_by_selector:
            blocks_by_selector[selector] = []
        blocks_by_selector[selector].extend(decl_dict.values())

    # Step 2: Sort selectors alphabetically
    sorted_selectors = sorted(blocks_by_selector.keys())

    # Step 3: Build normalized output
    result_parts = []

    # Add preamble (@define-color and other directives)
    preamble = parsed.get("preamble", "").strip()
    if preamble:
        result_parts.append(preamble)
        result_parts.append("")

    # Add each selector block
    for selector in sorted_selectors:
        declarations = blocks_by_selector[selector]
        # Remove duplicates but preserve order of appearance
        seen = set()
        unique_declarations = []
        for decl in reversed(declarations):
            prop = decl.split(":", 1)[0].strip()
            if prop not in seen:
                seen.add(prop)
                unique_declarations.append(decl)
        unique_declarations = list(reversed(unique_declarations))

        if unique_declarations:
            block_text = f"{selector} {{\n"
            for decl in unique_declarations:
                block_text += f"  {decl}\n"
            block_text += "}"
        else:
            block_text = f"{selector} {{\n}}"

        result_parts.append(block_text)
        result_parts.append("")

    # Add suffix if exists
    if parsed.get("suffix", "").strip():
        result_parts.append(parsed["suffix"].strip())

    return "\n".join(result_parts).strip() + "\n"


def read_gtk_css(theme_dir):
    css_paths = get_gtk_css_paths(theme_dir)

    if not css_paths:
        raise FileNotFoundError("No gtk.css found")

    files = {}

    for path in css_paths:
        with open(path, "r", encoding="utf-8") as f:
            files[path] = f.read()

    return files


def load_and_normalize_gtk_css(theme_dir):
    css_files = read_gtk_css(theme_dir)

    normalized = {}

    for path, css in css_files.items():
        normalized[path] = normalize_gtk_css(css)

    return normalized


def verify_css_rendering_identical(original_css, normalized_css):
    """Verify that normalized CSS would render identically to the original.
    
    Returns (is_safe, issues) where:
    - is_safe: True if renaming is safe
    - issues: List of potential rendering issues found
    """
    issues = []
    
    # Parse both versions
    original_parsed = parse_gtk_css(original_css)
    normalized_parsed = parse_gtk_css(normalized_css)
    
    if not original_parsed or not normalized_parsed:
        return False, ["Failed to parse CSS"]
    
    # Get all selectors from both
    original_selectors = {b['selector'] for b in original_parsed.get('blocks', [])}
    normalized_selectors = {b['selector'] for b in normalized_parsed.get('blocks', [])}
    
    # Check if selector sets match
    if original_selectors != normalized_selectors:
        missing = original_selectors - normalized_selectors
        extra = normalized_selectors - original_selectors
        if missing:
            issues.append(f"Missing selectors: {missing}")
        if extra:
            issues.append(f"Extra selectors: {extra}")
        return False, issues
    
    # Check each selector's properties
    original_by_sel = {}
    for b in original_parsed.get('blocks', []):
        sel = b['selector']
        if sel not in original_by_sel:
            original_by_sel[sel] = []
        original_by_sel[sel].append(b['declarations'].strip())
    
    normalized_by_sel = {}
    for b in normalized_parsed.get('blocks', []):
        sel = b['selector']
        if sel not in normalized_by_sel:
            normalized_by_sel[sel] = []
        normalized_by_sel[sel].append(b['declarations'].strip())
    
    # For each selector, merge all declarations and compare
    for sel in original_selectors:
        orig_props = set()
        for decl in original_by_sel.get(sel, []):
            for line in decl.splitlines():
                if ':' in line:
                    prop = line.split(':', 1)[0].strip()
                    orig_props.add(prop)
        
        norm_props = set()
        for decl in normalized_by_sel.get(sel, []):
            for line in decl.splitlines():
                if ':' in line:
                    prop = line.split(':', 1)[0].strip()
                    norm_props.add(prop)
        
        if orig_props != norm_props:
            issues.append(f"Property mismatch in {sel}: lost {orig_props - norm_props}")
            return False, issues
    
    return True, []


def save_gtk_css(css_files):
    for path, css_text in css_files.items():
        with open(path, "w", encoding="utf-8") as f:
            f.write(css_text)


def read_gtk_css_blocks(theme_dir):
    css_files = read_gtk_css(theme_dir)

    results = {}

    for path, css_text in css_files.items():
        parsed = parse_gtk_css(css_text)

        if not parsed:
            continue

        blocks = []

        for b in parsed.get("blocks", []):
            blocks.append({
                "prefix": b.get("prefix", ""),
                "selector": b.get("selector", "").strip(),
                "declarations": b.get("declarations", "").strip(),
            })

        results[path] = blocks

    return results

def get_css_value(blocks, selector, property_name):
    for block in blocks:
        if block["selector"] != selector:
            continue

        declarations = block["declarations"]

        for line in declarations.splitlines():
            line = line.strip()

            if not line or ":" not in line:
                continue

            prop, value = line.split(":", 1)

            if prop.strip() == property_name:
                return value.strip().rstrip(";")

    return None


def ensure_theme_temp_dir(theme_name):
    """Ensure the workspace temp directory for a theme exists and return its path.

    Path used: ~/.xfce-theme-studio/theme/{theme_name}.temp
    """
    temp_dir = Path.home() / ".xfce-theme-studio" / "theme" / f"{theme_name}.temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return str(temp_dir)


def copy_css_to_temp(original_css_path, theme_name):
    """Copy a GTK CSS file to the theme temp directory and return destination path.

    If the file already exists in temp, it is not recopied.
    The original GTK CSS path is preserved inside the temp folder (e.g. gtk-3.0/gtk.css).
    """
    temp_dir = ensure_theme_temp_dir(theme_name)
    original_css_path = os.path.abspath(original_css_path)
    rel_path = None

    for folder in GTK3_FOLDERS:
        marker = os.sep + folder + os.sep
        idx = original_css_path.rfind(marker)
        if idx != -1:
            rel_path = original_css_path[idx + 1:]
            break

    if rel_path is None:
        rel_path = os.path.basename(original_css_path)

    dest = os.path.join(temp_dir, rel_path)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if not os.path.exists(dest):
        shutil.copy2(original_css_path, dest)
    return dest


def _modify_css_text(css_text, selector, property_name, value):
    """Modify or create a property for a selector in the provided CSS text.

    Behavior:
    - parse the CSS into selector blocks
    - merge declarations for identical selectors (preserve order)
    - replace the last occurrence of the property if present, otherwise append it
    - if selector doesn't exist, create it
    - sort selectors alphabetically when rebuilding the CSS

    Returns updated CSS text.
    """
    if css_text is None:
        return ""

    parsed = parse_gtk_css(css_text)
    if not parsed:
        parsed = {"blocks": [], "suffix": "", "preamble": ""}

    # Collect declarations per selector preserving appearance order
    blocks_by_selector = {}
    for b in parsed.get("blocks", []):
        sel = b.get("selector", "").strip()
        decls = b.get("declarations", "").splitlines()

        if not sel:
            continue

        if sel not in blocks_by_selector:
            blocks_by_selector[sel] = []

        for line in decls:
            l = line.strip()
            if not l or l.startswith("/*"):
                continue
            if ":" in l:
                # store without trailing semicolon for uniformity
                blocks_by_selector[sel].append(l.rstrip(";"))

    # Prepare the new property line (without semicolon)
    new_prop_line = f"{property_name}: {value}".strip()

    # Insert or replace property for the selector
    if selector in blocks_by_selector:
        entries = blocks_by_selector[selector]
        last_idx = -1
        for i, e in enumerate(entries):
            prop = e.split(":", 1)[0].strip()
            if prop == property_name:
                last_idx = i

        if last_idx >= 0:
            entries[last_idx] = new_prop_line
        else:
            entries.append(new_prop_line)

        blocks_by_selector[selector] = entries
    else:
        blocks_by_selector[selector] = [new_prop_line]

    # Rebuild CSS: preamble, sorted selectors, suffix
    parts = []
    preamble = parsed.get("preamble", "").strip()
    if preamble:
        parts.append(preamble)
        parts.append("")

    for sel in sorted(blocks_by_selector.keys()):
        entries = blocks_by_selector[sel]

        # remove duplicate properties keeping the last occurrence
        seen = set()
        unique = []
        for e in reversed(entries):
            prop = e.split(":", 1)[0].strip()
            if prop not in seen:
                seen.add(prop)
                unique.append(e)
        unique = list(reversed(unique))

        block_text = f"{sel} {{\n"
        for e in unique:
            line = e.strip()
            if not line.endswith(";"):
                line = line + ";"
            block_text += f"  {line}\n"
        block_text += "}"

        parts.append(block_text)
        parts.append("")

    suffix = parsed.get("suffix", "").strip()
    if suffix:
        parts.append(suffix)

    return "\n".join(parts).strip() + "\n"


def update_css_file(temp_css_path, selector, property_name, value):
    """Update the CSS file at `temp_css_path` changing/adding `property_name` under `selector`.

    The file is overwritten with the modified CSS and the path is returned.
    """
    with open(temp_css_path, "r", encoding="utf-8") as f:
        original = f.read()

    updated = _modify_css_text(original, selector, property_name, value)

    with open(temp_css_path, "w", encoding="utf-8") as f:
        f.write(updated)

    return temp_css_path


def commit_temp_to_original(temp_css_path, original_css_path):
    """Copy the temp css back to the original location and remove the temp file.

    Attempts to remove the temp directory if it becomes empty.
    """
    shutil.copy2(temp_css_path, original_css_path)

    try:
        os.remove(temp_css_path)
    except OSError:
        pass

    temp_dir = os.path.dirname(temp_css_path)
    try:
        if os.path.isdir(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)
    except Exception:
        pass


def set_property_in_theme(theme_name, original_css_path, selector, property_name, value):
    """High-level helper: ensure temp copy, update property and return temp file path.

    - copies original css into ~/.xfce-theme-studio/theme/{theme_name}.temp/ if needed
    - updates the selector/property with the provided value
    - returns the path to the temp css file that was modified
    """
    temp_css = copy_css_to_temp(original_css_path, theme_name)
    update_css_file(temp_css, selector, property_name, value)
    return temp_css