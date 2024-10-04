import re
from PyPDF2 import PdfReader

def query_add_md(q: str):
    if not q.endswith('.') or not q.endswith('?'):
        q = q + '.'
    return q + "save the result in a json format, the keys are result, your confidence level(high/middle/low), and evidence."

def read_all_pdf_content(file_path):
    reader = PdfReader(file_path)
    first_page = 0
    if reader.pages[0].extract_text().find('To cite this article') > 0:
        first_page = 1
    all_content = ''
    for i in range(first_page, len(reader.pages)):
        all_content += reader.pages[i].extract_text()
    return all_content

def replace_ignore_case(string, old, new):
    pattern = re.compile(re.escape(old), re.IGNORECASE)
    return pattern.sub(new, string)

if __name__ == '__main__':
    pass