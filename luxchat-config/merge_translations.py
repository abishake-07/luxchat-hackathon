import sys

def extract_key(line):
    parts = line.split('"')
    if len(parts) > 1:
        return parts[1]
    return None

def format_line(src_line, dest_line):
    src_line = src_line.rstrip()
    dest_line = dest_line.rstrip()
    if dest_line.endswith(','):
        if not src_line.endswith(','):
            src_line += ','
    else:
        src_line = src_line.rstrip(',')
    return src_line + '\n'

def remove_and_add_last_brace(dest_path, updated_dest_lines):
    with open(dest_path, 'r', encoding='utf-8') as dest_file:
        dest_lines = dest_file.readlines()

    last_brace_index = -1
    for i, line in enumerate(reversed(dest_lines)):
        last_brace_index = len(dest_lines) - 1 - i
        if '}' in line:
            break

    if last_brace_index != -1:
        # Get the current line where the last '}' is found
        line_with_last_brace = dest_lines[last_brace_index]
        # Find the position of the last '}'
        last_brace_position = line_with_last_brace.rfind('}')
        # Remove the last '}' and any trailing whitespace before it, then append the rest of the line
        modified_line = line_with_last_brace[:last_brace_position].rstrip() + line_with_last_brace[last_brace_position+1:] + "\n"
        # Update the line in dest_lines
        dest_lines[last_brace_index] = modified_line

        # Add a comma after the penultimate '}'
        if last_brace_index > 1:
            dest_lines[last_brace_index - 1] = dest_lines[last_brace_index - 1].rstrip(',') + ','

        # Add the last '}' at the end of the file
        dest_lines.append('}\n')

        # Write back the updated destination JSON
        with open(dest_path, 'w', encoding='utf-8') as dest_file:
            dest_file.writelines(dest_lines)

def process_files(source_path, dest_path):
    with open(source_path, 'r', encoding='utf-8') as src_file:
        src_lines = src_file.readlines()

    src_dict = {extract_key(line): line for line in src_lines if extract_key(line)}

    with open(dest_path, 'r', encoding='utf-8') as dest_file:
        dest_lines = dest_file.readlines()

    updated_dest_lines = []
    for line in dest_lines:
        key = extract_key(line)
        if key in src_dict:
            updated_dest_lines.append(format_line(src_dict[key], line))
            del src_dict[key]
        else:
            updated_dest_lines.append(line)

    # Add remaining lines from source
    updated_dest_lines.extend(src_dict.values())

    # Write back the updated destination JSON
    with open(dest_path, 'w', encoding='utf-8') as dest_file:
        dest_file.writelines(updated_dest_lines)

    # Remove the last '}' and add it at the end with a comma after the penultimate '}'
    remove_and_add_last_brace(dest_path, updated_dest_lines)

def main():
    language = ["fr.json", "en_EN.json", "de_DE.json"]

    for handled_language in language:
        source_path = f"deltas/strings/{handled_language}"
        dest_path = f"src/i18n/strings/{handled_language}"

        try:
            process_files(source_path, dest_path)

        except FileNotFoundError as e:
            print(f"Error: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
