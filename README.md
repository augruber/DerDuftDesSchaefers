# Der Duft des Schäfers

LaTex project for the book "Der Duft des Schäfers".

## Project Structure
- `book/`: Contains the main LaTeX source and chapters.
  - `book/main.tex`: The main entry point.
  - `book/chapters/`: Individual LaTeX files for each chapter.
- `media/`: Images and static assets.
- `scripts/`: Utility scripts (legacy).

## Utility Tools

### Character & Word Count
To calculate accurate statistics for publishers (words, characters with and without spaces), use the provided Python script:

```bash
python3 count_chars.py
```

This script parses `book/main.tex` to find all included chapters and accurately strips LaTeX syntax while preserving your prose.

## Compilation
To compile the book to PDF, ensured you have a TeX distribution (like TeX Live or MacTeX) installed and run:

```bash
cd book
xelatex main.tex
```
