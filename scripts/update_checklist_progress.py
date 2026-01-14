import re

def update_progress(file_path):
    """
    Reads the checklist file, counts checked and total items,
    calculates progress percentage, and updates the HTML progress bar.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Count checked items (- [x])
    checked = len(re.findall(r'^- \[x\]', content, re.MULTILINE))

    # Count total items (- [x] or - [ ])
    total = len(re.findall(r'^- \[(?:x| )\]', content, re.MULTILINE))

    if total == 0:
        print("No checklist items found. Skipping update.")
        return

    # Calculate percentage (rounded to nearest int)
    percentage = round((checked / total) * 100)

    # Update aria-valuenow
    content = re.sub(r'aria-valuenow="\d+"', f'aria-valuenow="{percentage}"', content)

    # Update width styles (affects both outer and inner divs)
    content = re.sub(r'style="width:\d+%', f'style="width:{percentage}%', content)

    # Update the span text and ensure style is preserved
    span_pattern = r'<span[^>]*>\d+% · \d+/\d+</span>'
    new_span = f'<span style="display:inline-block; background:rgba(0,0,0,0.12); padding:4px 8px; border-radius:999px; font-size:0.95em;">{percentage}% · {checked}/{total}</span>'
    content = re.sub(span_pattern, new_span, content)

    # Write back to file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Updated progress: {percentage}% ({checked}/{total})")

if __name__ == "__main__":
    # Hardcoded path for solo development; adjust if needed
    checklist_path = "/home/dee/workspace/AI/Repo-Scanner/docs/sme_checklist.md"
    update_progress(checklist_path)