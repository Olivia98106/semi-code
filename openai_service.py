import dotenv
import os
import PyPDF2
import openai
import fitz  # PyMuPDF
import random
import util

dotenv.load_dotenv()
openai_key = os.getenv('OPENAI_KEY')

gpt3_model = 'gpt-3.5-turbo-1106'
fine_tuned_model = 'ft:gpt-3.5-turbo-1106:personal:label-datatype:9qirU0Ny'
gpt4o_model = "gpt-4o"
gpt4 = "gpt-4-turbo"


def pdf_to_text(pdf_file_path, binsize=1, abstract=1, start_ratio=0.3, end_ratio=0.76):
    try:
        with open(pdf_file_path, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ''
            if binsize == 1:
                start_num = 0
                end_num = len(pdf_reader.pages)
            else:
                start_num = int(start_ratio * len(pdf_reader.pages))
                end_num = int(end_ratio * len(pdf_reader.pages))
            if abstract == 1:
                # include the first two pages
                text += pdf_reader.pages[0].extract_text() if pdf_reader.pages[0].extract_text() else ''
                text += pdf_reader.pages[1].extract_text() if pdf_reader.pages[1].extract_text() else ''
            for page_num in range(start_num, end_num):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() if page.extract_text() else ''

            return text
    except PyPDF2.errors.PdfReadError:
        print(f"Error reading {pdf_file_path}: EOF marker not found")
        # corrupted_pdf[label] = corrupted_pdf[label].append(pdf_file_path)
        return None


def get_answer(knowledge_base, query, model):
    client = openai.Client()
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system",
             "content": 'you are a social scentist with a PhD in communication and media. You have read a paper as below:' + knowledge_base},
            {"role": "user", "content": query}
        ])
    return completion.choices[0].message.content


def chat_with_pdf(pdf_file_path, query):
    if pdf_file_path:
        knowledge_base = pdf_to_text(pdf_file_path)
        if query:
            response = get_answer(knowledge_base, query, model=gpt4o_model)
            return response


if __name__ == "__main__":
    q = '''
Analyze the following academic article and check if the authors use time-relevant phrases to 1) describe data collection procedure; 2) descriptive findings; 3) imply core concepts about time; 4) introduce time-relevant model specification. If no time-relevant phrase is found, return an empty string. Otherwise, extract the exact text where the authors give statements about time.
Make sure to:
Extract as comprehensively as possible.
Quote only the original text—do not fabricate any content. After the extraction, summarize the authors' motivation to use time-relevant phrases in a few words according to the four types provided. Do not add any additional commentary or text.
After the extraction, summarize the authors' motivation in a few words. Return the result in a json array, the json array contains json objects like:
{
"result": "extracted time-relevant phrases or empty string",
"summary": “motivation to use time-relevant phrase”
}
Do not add any additional commentary or text. Only return the output in the specified format.
    '''
    result = chat_with_pdf(
        'resources/pdf/10.1177&0093650219872394.pdf',
        q)
    print(result)