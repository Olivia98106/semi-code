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

if 'doc_id' not in st.session_state:
    st.session_state['doc_id'] = None

if 'hash' not in st.session_state:
    st.session_state['hash'] = None

if 'git_rev' not in st.session_state:
    st.session_state['git_rev'] = "unknown"
    if os.path.exists("revision.txt"):
        with open("revision.txt", 'r') as fr:
            from_file = fr.read()
            st.session_state['git_rev'] = from_file if len(from_file) > 0 else "unknown"

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
    layout="wide",
    menu_items={
        'Get Help': 'https://github.com/lfoppiano/pdf-struct',
        'Report a bug': "https://github.com/lfoppiano/pdf-struct/issues",
        'About': "View the structures extracted by Grobid."
    }
)

# from glob import glob
# import streamlit as st
#
# paths = glob("/Users/lfoppiano/kDrive/library/articles/materials informatics/polymers/*.pdf")
# for id, (tab,path) in enumerate(zip(st.tabs(paths),paths)):
#     with tab:
#         with st.container(height=600):
#             pdf_viewer(path, width=500, render_text=True)


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
    width = st.slider(label="PDF width", min_value=100, max_value=1000, value=1000)
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

    # st.header("Documentation")
    # st.markdown("https://github.com/lfoppiano/structure-vision")
    # st.markdown(
    #     """Upload a scientific article as PDF document and see the structures that are extracted by Grobid""")
    #
    # if st.session_state['git_rev'] != "unknown":
    #     st.markdown("**Revision number**: [" + st.session_state[
    #         'git_rev'] + "](https://github.com/lfoppiano/structure-vision/commit/" + st.session_state['git_rev'] + ")")


def new_file():
    st.session_state['doc_id'] = None
    st.session_state['uploaded'] = True
    st.session_state['annotations'] = []
    st.session_state['binary'] = None


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

with open('resources/chain.json') as f:
    chain_json = json.load(f)
    variables = [k for k in chain_json if k != 'summary']
pdf_csv_path = 'resources/A2.csv'
pdf_csv = pd.read_csv(pdf_csv_path)
doc_ids = pdf_csv['DOC_ID'].to_list()

st.title("PDF Viewer and Summary")
doc_id_selection = st.selectbox("Choose a PDF", doc_ids, index=None, key="doc_id_selection_key")
col1, col2 = st.columns(2)

if doc_id_selection:
    logging.info("doc id selected")
    new_file()
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
        with col1:
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
        with col2:
            st.write(f"Summary of {doc_id_selection}: ")
            st.text_area("Summary", summary, height=int(height / 2))
            st.write("AI labeling area")
            variable_selection = st.selectbox("Select a Variable:", variables, index=None)
            if variable_selection:
                with st.form("ai labeling form"):
                    st.write(f"AI labeling area for: {variable_selection}")
                    query = chain_json[variable_selection]
                    variable_response = str(openai_service.chat_with_pdf(pdf_path, util.query_add_md(query)))
                    logging.info(variable_response)
                    variable_response = variable_response[variable_response.find("{") : variable_response.rfind("}") + 1]
                    result, confidence_level, evidence = None, None, None
                    try:
                        variable_json = json.loads(variable_response)
                        if "result" in variable_json:
                            raw_result = str(variable_json["result"])
                            result = raw_result.replace(",", "")
                        else:
                            result = 'failed to get result from openai'
                        if "confidence level" in variable_json:
                            confidence_level = variable_json["confidence level"]
                        if "confidence_level" in variable_json:
                            confidence_level = variable_json["confidence_level"]
                        if "evidence" in variable_json:
                            evidence = variable_json["evidence"]
                    except:
                        st.write(f"Failed to parse json. Print raw json: \n{variable_response}")
                    variable_text = st.text_area("AI variable", result)
                    st.write(f"evidence: {evidence}")
                    st.write(f"confidence level: {confidence_level}")
                    st.write(f"page number from AI: not support yet")
                    submit_ai_labeling_form = st.form_submit_button("Apply AI variable")
                    if submit_ai_labeling_form:
                        pdf_csv.loc[doc_ids.index(doc_id_selection), variable_selection] = variable_text
                        pdf_csv.to_csv(pdf_csv_path, index=False)
                st.write("Manual labeling area")
                with st.form("Manual labeling form"):
                    st.write(f"Manual labeling area for: {variable_selection}")
                    manual_variable_selection = st.selectbox("Label:", ["others"])
                    manual_variable_input = st.text_input("input variable value")
                    submit_manual_labeling_form = st.form_submit_button("Apply manual variable")
                    if submit_manual_labeling_form:
                        pdf_csv.loc[doc_ids.index(doc_id_selection), variable_selection] = variable_text
                        pdf_csv.to_csv(pdf_csv_path, index=False)
