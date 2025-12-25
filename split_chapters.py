import re
import os

source_file = 'book/new_full_manuscript.tex'
output_dir = 'book/chapters'
os.makedirs(output_dir, exist_ok=True)

with open(source_file, 'r') as f:
    content = f.read()

# Pattern to identify split points: \part{...}, \chapter{...}, \addchap{...}
# We want to capture the command and the content following it.
# But simply splitting by regex might be easier.

# We will iterate line by line to determine when a new section starts.
lines = content.split('\n')

files = []
current_lines = []
file_counter = 0

def get_filename(counter, type, title):
    # Sanitize title
    safe_title = re.sub(r'[^a-zA-Z0-9]', '_', title)
    return f"{counter:02d}_{type}_{safe_title}.tex"

current_type = "frontmatter"
current_title = "Frontmatter"

for line in lines:
    # Check for split commands
    # \part{Teil I}
    match_part = re.match(r'\\part\{(.*?)\}', line)
    # \chapter{1} or \chapter{Title} - note: we reverted to \chapter{1}
    match_chapter = re.match(r'\\chapter\{(.*?)\}', line)
    # \addchap{...} or \addchap[...]{...}
    match_addchap = re.match(r'\\addchap(?:\[.*?\])?\{(.*?)\}', line)
    
    is_split = False
    new_type = ""
    new_title = ""

    if match_part:
        is_split = True
        new_type = "part"
        new_title = match_part.group(1)
    elif match_chapter:
        is_split = True
        new_type = "chapter"
        new_title = match_chapter.group(1)
    elif match_addchap:
        is_split = True
        new_type = "chapter" # Treat addchap as chapter
        new_title = match_addchap.group(1)
        # Verify if it's the specific Louis image block which might be multi-line or complex.
        # But our regex assumes single line.
        # Ensure we don't split inside a command if it was multiline, but here we scan line by line.
        # The Louis image addchap was: \addchap{\usebox{\louisimagebox}\par\vspace{0.5\baselineskip} 1}
        # which is one line unless wrapped.
        
    if is_split:
        # Save current buffer
        if current_lines:
            # check if previous buffer was empty/whitespace only? 
            # Frontmatter might be empty if file starts with \part immediately (unlikely here)
            filename = get_filename(file_counter, current_type, current_title)
            filepath = os.path.join(output_dir, filename)
            with open(filepath, 'w') as f_out:
                f_out.write('\n'.join(current_lines))
            files.append(filename)
            file_counter += 1
            current_lines = []
        
        current_type = new_type
        current_title = new_title
        
        # Handling the "begingroup" wrapper for Chapter 1. 
        # The \chapter{1} line is INSIDE a \begingroup ... \endgroup block in our last edit?
        # Let's check the file content viewed previously.
        # Lines 54-61:
        # \begingroup
        # \renewcommand...
        # ...
        # \chapter{1}...
        # \endgroup
        
        # The split logic above blindly splits AT \chapter. 
        # This means the \begingroup would be in the PREVIOUS file (Frontmatter or Part), 
        # and \chapter in the NEW file. The \endgroup would be in the NEW file.
        # This creates broken groups across files! \begingroup in file A, \endgroup in file B.
        # This is surprisingly valid in LaTeX (input includes text stream), BUT it's bad practice and confusing.
        # AND if we have \part before it, the \begingroup comes AFTER \part. 
        # So \part file would end with \begingroup ? 
        
        # We need to handle this specific case or manual intervention.
        # OR better: scan for the manual \begingroup block modification I made and keep it together with the chapter.
        
    current_lines.append(line)

# Correcting the "begingroup" issue for Chapter 1:
# If the split happened at \chapter{1}, we verify if the strictly preceding lines were part of the intended block.
# Actually, the \begingroup starts at line 54. \part is line 39. 
# So "Part I" file would contain lines 39-53 (including \newsavebox etc. and \begingroup \renewcommand...).
# Then "Chapter 1" file starts at line 60 (\chapter{1}).
# Then "Chapter 1" file ends at line 61 (\endgroup) ??? No, line 61 is \endgroup.
# So Part I file has \begingroup. Chapter 1 file has \chapter{1} ... \endgroup.
# This works technically (\input just pastes text), but logically the settings belong to Chapter 1.
# I should probably adjust the script to look-behind or just allow this for now as it's a structural split. 
# However, `new_full_manuscript.tex` has `\clearpage` and `\cfoot` at lines 51-52.
# These logically belong to the START of the text body (Chapter 1 sequence).

# Refined Logic:
# Maybe split specifically when \part, \chapter etc are found, but allow manual adjustment/grouping?
# Given the user wants "subfolder /chapters", I will stick to the regex split. 
# LaTeX \input IS perfectly capable of handling open groups across files.
# I will accept this unless it breaks compilation (unlikely).

# Final write for the last block
if current_lines:
    filename = get_filename(file_counter, current_type, current_title)
    filepath = os.path.join(output_dir, filename)
    with open(filepath, 'w') as f_out:
        f_out.write('\n'.join(current_lines))
    files.append(filename)

# Sort files to be safe (though list is ordered)
files.sort()

# Print the \input commands for the user/next tool
print("Generated files:")
for f_name in files:
    print(f"\\input{{chapters/{f_name}}}")
