import os
from hashlib import blake2b
from tempfile import NamedTemporaryFile
import pandas as pd
import dotenv
from grobid_client.grobid_client import GrobidClient
from streamlit_pdf_viewer import pdf_viewer
from grobid.grobid_processor import GrobidProcessor
import openai_service
import json
import streamlit as st
import logging
import util

logging.basicConfig(level=logging.INFO)
dotenv.load_dotenv(override=True)

variable_select_box_key = 'variable_select_box_key'
if 'doc_id' not in st.session_state:
    st.session_state['doc_id'] = None

if 'hash' not in st.session_state:
    st.session_state['hash'] = None

if 'uploaded' not in st.session_state:
    st.session_state['uploaded'] = False

if 'binary' not in st.session_state:
    st.session_state['binary'] = None

if 'annotations' not in st.session_state:
    st.session_state['annotations'] = []

if 'pages' not in st.session_state:
    st.session_state['pages'] = None

if 'page_selection' not in st.session_state:
    st.session_state['page_selection'] = []

st.set_page_config(
    page_title="PDF Viewer and Summary",
    page_icon="",
    initial_sidebar_state="expanded",
    layout="wide"
)


with st.sidebar:
    st.header("Text")
    enable_text = st.toggle('Render text in PDF', value=True, disabled=not st.session_state['uploaded'],
                            help="Enable the selection and copy-paste on the PDF")

    st.header("Highlights")
    highlight_title = st.toggle('Title', value=False, disabled=not st.session_state['uploaded'])
    highlight_person_names = st.toggle('Person Names', value=False, disabled=not st.session_state['uploaded'])
    highlight_affiliations = st.toggle('Affiliations', value=False, disabled=not st.session_state['uploaded'])
    highlight_head = st.toggle('Head of sections', value=False, disabled=not st.session_state['uploaded'])
    highlight_sentences = st.toggle('Sentences', value=True, disabled=not st.session_state['uploaded'])
    highlight_paragraphs = st.toggle('Paragraphs', value=True, disabled=not st.session_state['uploaded'])
    highlight_notes = st.toggle('Notes', value=False, disabled=not st.session_state['uploaded'])
    highlight_formulas = st.toggle('Formulas', value=False, disabled=not st.session_state['uploaded'])
    highlight_figures = st.toggle('Figures and tables', value=True, disabled=not st.session_state['uploaded'])
    highlight_callout = st.toggle('References citations in text', value=False, disabled=not st.session_state['uploaded'])
    highlight_citations = st.toggle('Citations', value=False, disabled=not st.session_state['uploaded'])

    st.header("Annotations")
    annotation_thickness = st.slider(label="Annotation boxes border thickness", min_value=1, max_value=6, value=1)
    pages_vertical_spacing = st.slider(label="Pages vertical spacing", min_value=0, max_value=10, value=2)

    st.header("Height and width")
    resolution_boost = st.slider(label="Resolution boost", min_value=1, max_value=10, value=1)
    width = st.slider(label="PDF width", min_value=100, max_value=2000, value=2000)
    height = st.slider(label="PDF height", min_value=100, max_value=1000, value=1000)

    st.header("Page Selection")
    placeholder = st.empty()

    if not st.session_state['pages']:
        st.session_state['page_selection'] = placeholder.multiselect(
            "Select pages to display",
            options=[],
            default=[],
            help="The page number considered is the PDF number and not the document page number.",
            disabled=not st.session_state['pages'],
            key=1
        )


def new_file():
    st.session_state['doc_id'] = None
    st.session_state['uploaded'] = True
    st.session_state['annotations'] = []
    st.session_state['binary'] = None
    st.session_state[variable_select_box_key] = None

@st.cache_resource
def init_grobid():
    grobid_client = GrobidClient(
        grobid_server='http://localhost:8070/',
        batch_size=1000,
        coordinates=["p", "s", "persName", "biblStruct", "figure", "formula", "head", "note", "title", "ref",
                     "affiliation"],
        sleep_time=5,
        timeout=60,
        check_server=True
    )
    grobid_processor = GrobidProcessor(grobid_client)

    return grobid_processor


init_grobid()

def get_file_hash(fname):
    hash_md5 = blake2b()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

with open('resources/chain.json') as f:
    chain_json = json.load(f)
    variables = [k for k in chain_json if k != 'summary']
pdf_csv_path = 'resources/A2.csv'
pdf_csv = pd.read_csv(pdf_csv_path, index_col='DOC_ID', sep='\t')
log_csv_path = 'resources/A2_log.csv'
log_csv = pd.read_csv(log_csv_path, index_col='DOC_ID', sep='\t')
doc_ids = pdf_csv.index.to_list()



st.title("PDF Viewer and Summary")
col1, col2 = st.columns(2)

with col1:
    with st.form("Private document indexing"):
        kw = st.text_input("Keywords")
        button = st.form_submit_button("OK")
        if button:
            pass

with col2:
    doc_id_selection = st.selectbox("Choose a PDF", doc_ids, index=None, on_change=new_file())
    if doc_id_selection:
        logging.info("doc id selected")
        filename = pdf_csv['Filename'][doc_ids.index(doc_id_selection)]
        pdf_path = os.path.join('resources/pdf', filename)
        summary = openai_service.chat_with_pdf(pdf_path, chain_json['summary'])
        if not st.session_state['binary']:
            with (st.spinner('Reading file, calling Grobid...')):
                with open(pdf_path, 'rb') as f:
                    binary = f.read()
                    tmp_file = NamedTemporaryFile()
                    tmp_file.write(bytearray(binary))
                    st.session_state['binary'] = binary
                    annotations, pages = init_grobid().process_structure(tmp_file.name)

                    st.session_state['annotations'] = annotations if not st.session_state['annotations'] else \
                        st.session_state[
                            'annotations']
                    st.session_state['pages'] = pages if not st.session_state['pages'] else st.session_state['pages']

        if st.session_state['pages']:
            st.session_state['page_selection'] = placeholder.multiselect(
                "Select pages to display",
                options=list(range(1, st.session_state['pages'])),
                default=[],
                help="The page number considered is the PDF number and not the document page number.",
                disabled=not st.session_state['pages'],
                key=2
            )

        with (st.spinner("Rendering PDF document")):
            annotations = st.session_state['annotations']

            if not highlight_sentences:
                annotations = list(filter(lambda a: a['type'] != 's', annotations))

            if not highlight_paragraphs:
                annotations = list(filter(lambda a: a['type'] != 'p', annotations))

            if not highlight_title:
                annotations = list(filter(lambda a: a['type'] != 'title', annotations))

            if not highlight_head:
                annotations = list(filter(lambda a: a['type'] != 'head', annotations))

            if not highlight_citations:
                annotations = list(filter(lambda a: a['type'] != 'biblStruct', annotations))

            if not highlight_notes:
                annotations = list(filter(lambda a: a['type'] != 'note', annotations))

            if not highlight_callout:
                annotations = list(filter(lambda a: a['type'] != 'ref', annotations))

            if not highlight_formulas:
                annotations = list(filter(lambda a: a['type'] != 'formula', annotations))

            if not highlight_person_names:
                annotations = list(filter(lambda a: a['type'] != 'persName', annotations))

            if not highlight_figures:
                annotations = list(filter(lambda a: a['type'] != 'figure', annotations))

            if not highlight_affiliations:
                annotations = list(filter(lambda a: a['type'] != 'affiliation', annotations))

            pdf_viewer(
                input=st.session_state['binary'],
                width=width,
                height=height,
                annotations=annotations,
                pages_vertical_spacing=pages_vertical_spacing,
                annotation_outline_size=annotation_thickness,
                pages_to_render=st.session_state['page_selection'],
                render_text=enable_text,
                resolution_boost=resolution_boost
            )


