import streamlit as st
import os
import pandas as pd
import json
import PyPDF2 
import fitz  # PyMuPDF
from streamlit_pdf_viewer import pdf_viewer
from dotenv import load_dotenv, find_dotenv
import openai

load_dotenv(find_dotenv())
openai.api_key = os.environ["OPENAI_API_KEY"]

# load env varibales
load_dotenv()

##################################################
# Define the models
gpt3_model = 'gpt-3.5-turbo-1106'
fine_tuned_model = 'ft:gpt-3.5-turbo-1106:personal:label-datatype:9qirU0Ny' 
gpt4o_model = "gpt-4o-mini"
gpt4 = "gpt-4-turbo"
##################################################

# Function to load a PDF file and render it in the Streamlit app
def display_pdf(uploaded_file):
  if uploaded_file:
        pdf_viewer(uploaded_file)
    # doc = fitz.open(pdf_path)
    # for page_num in range(len(doc)):
    #     page = doc.load_page(page_num)
    #     pix = page.get_pixmap()
    #     image_path = f"temp_{page_num}.png"
    #     pix.save(image_path)
    #     st.image(image_path)

# Function to load and display summary
def display_summary(summary_path):
    with open(summary_path, "r") as file:
        summary = file.read()
    st.text_area("Summary", summary, height=2500)

def pdf_to_text(pdf_file_path,binsize=1, abstract=1, start_ratio = 0.3, end_ratio=0.76):
    try:
        with open(pdf_file_path, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ''
            if binsize == 1:
                start_num = 0
                end_num = len(pdf_reader.pages)
            else:
                start_num = int(start_ratio*len(pdf_reader.pages))
                end_num = int(end_ratio*len(pdf_reader.pages))
            if abstract == 1:
                # include the first two pages
                text += pdf_reader.pages[0].extract_text() if pdf_reader.pages[0].extract_text() else ''
                text += pdf_reader.pages[1].extract_text() if pdf_reader.pages[1].extract_text() else ''
            for page_num in range(start_num,end_num):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() if page.extract_text() else ''
            
            return text
    except PyPDF2.errors.PdfReadError:
        print(f"Error reading {pdf_file_path}: EOF marker not found")
        # corrupted_pdf[label] = corrupted_pdf[label].append(pdf_file_path)
        return None

def get_answer(knowledgeBase,query,model):
    client = openai.Client()
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": 'you are a social scentist with a PhD in communication and media. You have read a paper as below:'+knowledgeBase},
            {"role": "user", "content": query}
        ])
    return completion.choices[0].message.content

def chat_with_pdf(pdf_file_path,query):
    if pdf_file_path:
        knowledgeBase = pdf_to_text(pdf_file_path)
        
    if query:
        response = get_answer(knowledgeBase,query,model=gpt4o_model)
        st.write(response)

# Streamlit App
def main():
    st.title("PDF Viewer and Summary")

    # List all PDFs and summaries in the respective folders
    pdf_files = os.listdir('pdf')
    pdf_files = [file for file in pdf_files if file.endswith(".pdf")]
    summary_files = os.listdir('data')
    summary_files = [file for file in summary_files if file.endswith(".txt")]

    # Ensure to display in a sorted order to match PDF with corresponding summary
    pdf_files.sort()
    summary_files.sort()

    
    # load filenames.csv
    df = pd.read_csv('filenames.csv')
    mapping_doc_file = dict(zip(df.Filename,df.DOC_ID))
    mapping_file_doc = dict(zip(df.DOC_ID,df.Filename))
    # Create a dropdown to select a PDF
    doi_ids = [mapping_doc_file[pdf] for pdf in pdf_files]
    pdf_selection = st.selectbox("Choose a PDF", doi_ids)

    

    # Display PDF and summary on horizontal columns
    col1, col2 = st.columns(2)
    if pdf_selection:
      filename = mapping_file_doc[pdf_selection]
      summary_selection = filename.split('.pdf')[0]+'.txt'
      #chat with pdf
      query = st.text_input('Ask question to PDF...')
      cancel_button = st.button('Cancel')
      if cancel_button:
          st.stop()
      chat_with_pdf(os.path.join('pdf', filename), query)

    if pdf_selection:
      with col1:
        st.header(f"Displaying: {mapping_doc_file[filename]}")
        st.text(f"Filename: {filename}")
        pdf_path = os.path.join('pdf', filename)
        display_pdf(pdf_path)
    
      with col2:
        st.header(f"Summary: {mapping_doc_file[filename]}")
        summary_path = os.path.join('data', summary_selection)
        display_summary(summary_path)

if __name__ == "__main__":
    main()
