"""
This python utility pulls together functions around read/write with logs or structured text files.
"""

import os

def read_file_lines(filepath, encoding='utf-8'):
    """Read all lines from a text file."""
    with open(filepath, 'r', encoding=encoding) as f:
        return f.readlines()

def write_lines(filepath, lines, encoding='utf-8'):
    """Write a list of lines to a text file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding=encoding) as f:
        f.writelines(lines)

def append_line(filepath, line, encoding='utf-8'):
    """Append a single line to a text file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'a', encoding=encoding) as f:
        f.write(line + '\n')

def ensure_dir_exists(path):
    """Ensure that a directory exists."""
    os.makedirs(path, exist_ok=True)


def write_debug_log(message, debug_path, encoding='utf-8'):
    """Write a debug message to a log file."""
    append_line(debug_path, message, encoding=encoding)
