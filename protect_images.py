import re

file_path = 'book/new_full_manuscript.tex'
with open(file_path, 'r') as f:
    lines = f.readlines()

new_lines = []
i = 0
in_center = False
buffer = []

while i < len(lines):
    line = lines[i]
    if '\\begin{center}' in line:
        # Check if we are already in a center block (nested? shouldn't be with my regex)
        # Assuming no nesting for these generated blocks
        if in_center:
             # Previous block didn't close? Dump it.
             new_lines.extend(buffer)
             buffer = []
        
        buffer = [line]
        in_center = True
        i += 1
        continue
    
    if in_center:
        buffer.append(line)
        if '\\end{center}' in line:
            # End of block. Analyze buffer.
            # Convert buffer to string to check for includegraphics
            block_content = "".join(buffer)
            if '\\includegraphics' in block_content:
                # Found an image block
                
                start_idx = 1
                end_idx = len(buffer) - 1
                
                # Check for vspace at start
                first_vspace = ""
                # Allow for blank lines before vspace
                while start_idx < end_idx:
                    if 'vspace' in buffer[start_idx]:
                        first_vspace = buffer[start_idx]
                        start_idx += 1
                        break
                    elif buffer[start_idx].strip() == "":
                        start_idx += 1
                    else:
                        break # Found content before vspace?
                
                # Check for vspace at end
                last_vspace = ""
                # Allow for blank lines after vspace
                while end_idx > start_idx:
                    if 'vspace' in buffer[end_idx - 1]:
                        last_vspace = buffer[end_idx - 1]
                        end_idx -= 1
                        break
                    elif buffer[end_idx - 1].strip() == "":
                         end_idx -= 1
                    else:
                        break

                inner_content = buffer[start_idx:end_idx]
                
                # Construct new block
                new_block = []
                new_block.append(buffer[0]) # \begin{center}
                if first_vspace: new_block.append(first_vspace)
                
                new_block.append("\\begin{minipage}{\\linewidth}\n")
                new_block.append("\\centering\n")
                new_block.extend(inner_content)
                new_block.append("\\end{minipage}\n")
                
                if last_vspace: new_block.append(last_vspace)
                new_block.append(buffer[-1]) # \end{center}
                
                new_lines.extend(new_block)
            else:
                # Not an image block
                new_lines.extend(buffer)
            
            in_center = False
            buffer = []
        i += 1
    else:
        new_lines.append(line)
        i += 1

# Flush any remaining buffer
if buffer:
    new_lines.extend(buffer)

with open(file_path, 'w') as f:
    f.writelines(new_lines)
