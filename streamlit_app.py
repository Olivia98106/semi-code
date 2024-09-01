import os
from hashlib import blake2b
from tempfile import NamedTemporaryFile
import pandas as pd
import dotenv
from grobid_client.grobid_client import GrobidClient
from streamlit_pdf_viewer import pdf_viewer

from grobid.grobid_processor import GrobidProcessor

dotenv.load_dotenv(override=True)

import streamlit as st

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
    enable_text = st.toggle('Render text in PDF', value=False, disabled=not st.session_state['uploaded'],
                            help="Enable the selection and copy-paste on the PDF")

    st.header("Highlights")
    highlight_title = st.toggle('Title', value=True, disabled=not st.session_state['uploaded'])
    highlight_person_names = st.toggle('Person Names', value=True, disabled=not st.session_state['uploaded'])
    highlight_affiliations = st.toggle('Affiliations', value=True, disabled=not st.session_state['uploaded'])
    highlight_head = st.toggle('Head of sections', value=True, disabled=not st.session_state['uploaded'])
    highlight_sentences = st.toggle('Sentences', value=False, disabled=not st.session_state['uploaded'])
    highlight_paragraphs = st.toggle('Paragraphs', value=True, disabled=not st.session_state['uploaded'])
    highlight_notes = st.toggle('Notes', value=True, disabled=not st.session_state['uploaded'])
    highlight_formulas = st.toggle('Formulas', value=True, disabled=not st.session_state['uploaded'])
    highlight_figures = st.toggle('Figures and tables', value=True, disabled=not st.session_state['uploaded'])
    highlight_callout = st.toggle('References citations in text', value=True, disabled=not st.session_state['uploaded'])
    highlight_citations = st.toggle('Citations', value=True, disabled=not st.session_state['uploaded'])

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

    st.header("Documentation")
    st.markdown("https://github.com/lfoppiano/structure-vision")
    st.markdown(
        """Upload a scientific article as PDF document and see the structures that are extracted by Grobid""")

    if st.session_state['git_rev'] != "unknown":
        st.markdown("**Revision number**: [" + st.session_state[
            'git_rev'] + "](https://github.com/lfoppiano/structure-vision/commit/" + st.session_state['git_rev'] + ")")


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


def get_file_hash(fname):
    hash_md5 = blake2b()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


st.title("PDF Viewer and Summary")
pdf_files = os.listdir('pdf')
pdf_files = [file for file in pdf_files if file.endswith(".pdf")]
summary_files = os.listdir('data')
summary_files = [file for file in summary_files if file.endswith(".txt")]
pdf_files.sort()
summary_files.sort()
df = pd.read_csv('filenames.csv')
mapping_doc_file = dict(zip(df.Filename,df.DOC_ID))
mapping_file_doc = dict(zip(df.DOC_ID,df.Filename))
doi_ids = [mapping_doc_file[pdf] for pdf in pdf_files]
pdf_selection = st.selectbox("Choose a PDF", doi_ids)

col1, col2 = st.columns(2)

if pdf_selection:
    new_file()
    filename = mapping_file_doc[pdf_selection]
    summary_selection = filename.split('.pdf')[0] + '.txt'
    pdf_path = os.path.join('pdf', filename)
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
            st.header(f"Summary: {mapping_doc_file[filename]}")
            summary_path = os.path.join('data', summary_selection)
            with open(summary_path, "r") as file:
                summary = file.read()
            st.text_area("Summary", summary, height=int(height/2))


