import re
import os

file_path = 'book/new_full_manuscript.tex'

with open(file_path, 'r') as f:
    lines = f.readlines()

new_lines = []
i = 0
first_image_skipped = False
# Regex for song caption: Text \textbf{...} (allow for various quote styles)
# Pandoc might use `` or " or «
song_caption_pattern = re.compile(r'.*\\textbf\{.*\}')

while i < len(lines):
    line = lines[i]
    
    if '\\includegraphics' in line:
        if not first_image_skipped:
            # Keep the first image (cover) as is
            new_lines.append(line)
            first_image_skipped = True
            i += 1
            continue
            
        # Check if the PREVIOUS line (ignoring empty lines) was a song caption
        # We need to look back at new_lines
        # The structure in file seems to be: Line Caption \n \n Line Image
        
        # Let's peek backwards in the original lines list to find the caption
        # There might be empty lines between caption and image
        
        caption_line_index = -1
        # Look back 1 or 2 lines for non-empty text
        for back_idx in range(1, 5): # Look back up to 4 lines
            if i - back_idx < 0: break
            prev_content = lines[i - back_idx].strip()
            if not prev_content: continue # skip empty
            
            # Found non-empty line. Is it a caption?
            if song_caption_pattern.match(prev_content):
                caption_line_index = i - back_idx
            break # Stop after finding closest text
            
        # We need to handle this carefully. Since I'm appending to new_lines, 
        # I might have already appended the caption.
        # It's easier to process this by grouping.
        
        # Actually, if I just modify the image line to be centered with spacing, 
        # and IF I find a caption, I wrap THAT too?
        # That requires modifying previously appended lines or changing iteration.
        
        # Simpler approach: 
        # If I detect this is an image that needs wrapping:
        # 1. Determine if it has a preceding caption.
        # 2. If yes, pop the caption (and intervening newlines) from new_lines?
        #    Or better: Identify "chunk" to wrap.
        
        # Let's try a forward-looking or state-machine approach isn't needed if we are careful.
        # The structure seems consistent: Caption \n \n Image
        
        # BUT wait: The user said "caption ... is considered part of the figure".
        # If I just center the Image, spacing might separate it from caption.
        # So I should wrap {Caption + Image} in the formatting block.
        
        has_caption = False
        caption_content = ""
        
        # Check new_lines for the caption
        # We need to find if the *immediately preceding non-empty line* in new_lines is a caption
        
        # Find last non-empty line index in new_lines
        last_text_idx = -1
        for idx in range(len(new_lines) - 1, -1, -1):
            if new_lines[idx].strip():
                last_text_idx = idx
                break
        
        if last_text_idx != -1:
            potential_caption = new_lines[last_text_idx]
            if song_caption_pattern.match(potential_caption.strip()):
                has_caption = True
                # We found a caption! We need to wrap from last_text_idx to current line.
                
                # Insert start of wrapper before caption
                new_lines.insert(last_text_idx, "\\begin{center}\n\\vspace{1.5\\baselineskip}\n")
                
                # Append image
                new_lines.append(line)
                
                # Append end of wrapper
                new_lines.append("\\vspace{1.5\\baselineskip}\n\\end{center}\n")
                
                i += 1
                continue

        # If no caption found found (or text didn't match pattern), just wrap image
        new_lines.append("\\begin{center}\n\\vspace{1.5\\baselineskip}\n")
        new_lines.append(line)
        new_lines.append("\\vspace{1.5\\baselineskip}\n\\end{center}\n")
        i += 1
        
    else:
        new_lines.append(line)
        i += 1

with open(file_path, 'w') as f:
    f.writelines(new_lines)
