# Step 1 — check if ToC is detected
python inspect_toc.py some_new.pdf

# Step 2 — if detected, check raw blocks
python inspect_toc.py some_new.pdf --debug

# Step 3 — if ToC not detected, check raw blocks manually with increased limit
python inspect_toc.py some_new.pdf --search-limit 50 --debug

# Step 4 — once ToC is found, verify parsing before generating files
python pdf_to_chapters.py some_new.pdf --debug

# Step 5 — generate
python pdf_to_chapters.py some_new.pdf

# Optional: if you want to check the raw text of the first few pages to understand the structure
python -c "
import fitz
doc = fitz.open('some_new.pdf')
for i in range(30):
    text = doc[i].get_text().strip()[:100]
    print(f'Page {i+1}: {repr(text)}')
"