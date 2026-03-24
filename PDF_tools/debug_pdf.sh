python -c "
import fitz
doc = fitz.open('The_Art_of_VA_Filter_Design-Vadim_Zavalishin_2.1.0.pdf')
for i in range(30):
    text = doc[i].get_text().strip()[:100]
    print(f'Page {i+1}: {repr(text)}')
"