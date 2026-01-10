#!/usr/bin/env python3
import re
import os
import argparse

def count_file(filepath):
    if not os.path.exists(filepath):
        return None
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Remove comments
    content = re.sub(r'%.*$', '', content, flags=re.MULTILINE)
    
    # 2. Extract content from common formatting commands while removing the command itself
    # e.g. \emph{text} -> text
    # This regex handles simple non-nested commands
    common_commands = ['emph', 'textbf', 'textit', 'songtext', 'indentedblock', 'section', 'part', 'chapter']
    for cmd in common_commands:
        content = re.sub(r'\\' + cmd + r'\{', '', content)
    
    # 3. Remove other LaTeX commands (\command or \command[opt]{arg})
    # This regex matches \name, \name[...], \name{...}
    # It removes the entire command and its arguments (like \qrblock{...}{...})
    content = re.sub(r'\\[a-zA-Z]+(\[[^\]]*\])?(\{.*?\})*', '', content, flags=re.DOTALL)
    
    # 4. Remove standalone braces (cleanup from step 2)
    content = content.replace('{', '').replace('}', '')
    
    # 5. Clean up extra whitespace but keep single spaces/newlines
    content = re.sub(r'[ \t]+', ' ', content)
    
    # Stats
    chars_with_spaces = len(content)
    chars_no_spaces = len(content.replace(" ", "").replace("\n", "").replace("\r", ""))
    words = len(content.split())
    
    return {
        "chars_with_spaces": chars_with_spaces,
        "chars_no_spaces": chars_no_spaces,
        "words": words
    }

def main():
    parser = argparse.ArgumentParser(description="Calculate word and character counts for the book.")
    parser.add_argument("--dir", default="book", help="Directory containing the LaTeX source (default: book)")
    parser.add_argument("--main", default="main.tex", help="Main LaTeX file (default: main.tex)")
    args = parser.parse_args()

    main_tex_path = os.path.join(args.dir, args.main)
    
    if not os.path.exists(main_tex_path):
        print(f"Error: Could not find {main_tex_path}")
        return

    with open(main_tex_path, 'r', encoding='utf-8') as f:
        main_content = f.read()
    
    # Find all \input{...} lines
    inputs = re.findall(r'\\input\{(.*?)\}', main_content)
    
    total = {"chars_with_spaces": 0, "chars_no_spaces": 0, "words": 0}
    
    print(f"{'File':<50} | {'Words':>8} | {'Chars+S':>8} | {'Chars-S':>8}")
    print("-" * 83)

    for inp in inputs:
        if not inp.endswith(".tex"):
            inp += ".tex"
        
        filepath = os.path.join(args.dir, inp)
        stats = count_file(filepath)
        
        if stats:
            print(f"{inp:<50} | {stats['words']:>8} | {stats['chars_with_spaces']:>8} | {stats['chars_no_spaces']:>8}")
            for key in total:
                total[key] += stats[key]
        else:
            print(f"{inp:<50} | {'MISSING':>8}")

    print("-" * 83)
    print(f"{'TOTAL':<50} | {total['words']:>8} | {total['chars_with_spaces']:>8} | {total['chars_no_spaces']:>8}")

if __name__ == "__main__":
    main()
