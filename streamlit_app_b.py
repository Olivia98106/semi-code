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
import sqlalchemy
from bs4 import BeautifulSoup

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

summary_prompt = "Please provide a summary of the research article focusing on the following aspects, using original phrases about time and unit of analysis from article if possible:\n- Research Method: Describe the overall research method employed in the study, also the data collection procedure and duration, time intervals\n- Time relevant details: state the data collection procedure and duration, time intervals of data collection between times. Usually research variables are collected each time.\n- Sampling Method and Entity Type: Explain the sampling method used and specify the type of entities (e.g., individuals, organizations) involved. Here, entity refers to an unit of analysis, or termed as analysis level, granuality or resolution. \n- Statistical Model: Outline the statistical model applied for analysis. DO NOT USE conceptual model name here.\n- Unit of Analysis: Identify the unit of analysis used in the statistical model.\n- Number of entities or Sample Size: the table and results parts ususally reveal the number of analysis unit.Analysis model details in figure and table are good references."
conn = st.connection('sqlite.db', type='sql', url='sqlite:///resources/sqlite.db')
chain = conn.query('select * from chain', ttl=0)
chain_dict = dict(zip(chain['variable'], chain['prompt']))

pdfs = conn.query('select * from pdf', ttl=0)
pdf_dict = dict(zip(pdfs['doc_id'], pdfs['filename']))

st.title("PDF Viewer and Summary")
doc_id_selection = st.selectbox("Choose a PDF", pdf_dict.keys(), index=None, on_change=new_file(), key="doc_id_selection")
col1, col2 = st.columns(2)

@st.fragment
def export_pdf_body():
    filename = pdf_dict[st.session_state['doc_id_selection']]
    filename = filename[:-4]
    logging.info(f"export pdf xml {filename}")
    with open(f"resources/xml/{filename}.grobid.tei.xml", "rb") as file:
        st.download_button(
            label="Download PDF Content as XML",
            data=file,
            file_name=f"{filename}.grobid.tei.xml",
            mime="text/xml",
        )

@st.fragment
def export_pdf_selected_content():
    # init_grobid().process_pdf_to_xml("resources/pdf", "resources/xml")
    filename = pdf_dict[st.session_state['doc_id_selection']]
    filename = filename[:-4]
    logging.info(f"export pdf select content {filename}")
    with open(f"resources/xml/{filename}.grobid.tei.xml", "rb") as file:
        soup = BeautifulSoup(file, features="xml")
        selected_content = {}
        if highlight_title:
            selected_content['title'] = [soup.title.text]
        if highlight_person_names:
            selected_content['person_names'] = []
            for persName in soup.find_all('persName'):
                pn = ''
                for name in persName.children:
                    pn = pn + name.text + " "
                selected_content['person_names'].append(pn)
        if highlight_figures:
            selected_content['figures'] = []
            for figure in soup.find_all('figure'):
                if figure.head:
                    selected_content['figures'].append(figure.head.text)
        if highlight_sentences or highlight_paragraphs:
            selected_content['paragraphs'] = []
            for paragraph in soup.find_all('p'):
                selected_content['paragraphs'].append(paragraph.text)
        st.download_button(
            label="Download Selected Content as JSON",
            data=json.dumps(selected_content),
            file_name=f"{filename}.json",
            mime="application/json",
        )

@st.fragment
def export_pdf_selected_content_as_txt():
    # init_grobid().process_pdf_to_xml("resources/pdf", "resources/xml")
    filename = pdf_dict[st.session_state['doc_id_selection']]
    filename = filename[:-4]
    logging.info(f"export pdf select content {filename}")
    with open(f"resources/xml/{filename}.grobid.tei.xml", "rb") as file:
        soup = BeautifulSoup(file, features="xml")
        selected_txt = soup.title.text + '\n\n'
        if highlight_person_names:
            for persName in soup.find_all('persName'):
                pn = ''
                for name in persName.children:
                    pn = pn + name.text + " "
                selected_txt = selected_txt + pn + '\n'
            selected_txt = selected_txt + '\n'
        if highlight_figures:
            for figure in soup.find_all('figure'):
                if figure.head:
                    selected_txt = selected_txt + figure.head.text + '\n'
            selected_txt = selected_txt + '\n'
        if highlight_sentences or highlight_paragraphs:
            for paragraph in soup.find_all('p'):
                selected_txt = selected_txt + paragraph.text + '\n'
        st.download_button(
            label="Download Selected Content as TXT",
            data=selected_txt,
            file_name=f"{filename}.txt"
        )

@st.fragment
def export_label_csv():
    label_df = conn.query(
        f"select doc_id, variable, label from label order by doc_id, variable", ttl=0)
    doc_ids = label_df['doc_id'].to_list()
    variables = label_df['variable'].to_list()
    labels = label_df['label'].to_list()
    doc_id_single = sorted(list(set(doc_ids)))
    variables_single = sorted(list(set(variables)))
    result_dict = {}
    result_dict['DOC_ID'] = doc_id_single
    for variable in variables_single:
        current_list = ['' for i in range(len(doc_id_single))]
        result_dict[variable] = current_list
    for i in range(len(doc_ids)):
        d = doc_ids[i]
        v = variables[i]
        l = labels[i]
        idx = doc_id_single.index(d)
        result_dict[v][idx] = l
    result_df = pd.DataFrame(result_dict)
    st.download_button(
        "Download Labels as CSV",
        result_df.to_csv(index=False, sep='\t').encode('utf-8'),
        "label.csv",
        "text/csv"
    )

@st.fragment
def export_log_csv():
    label_df = conn.query(
        f"select doc_id, variable, label, ai_label, manual_label, prompt_version from label order by doc_id, variable", ttl=0)
    st.download_button(
        "Download Logs as CSV",
        label_df.to_csv(index=False, sep='\t').encode('utf-8'),
        "log.csv",
        "text/csv"
    )


@st.fragment
def submit_label():
    variable_selection = st.session_state['variable_selection']
    variable_response = st.session_state['variable_response']
    variable_response = variable_response[variable_response.find("{"): variable_response.rfind("}") + 1]
    result, confidence_level, evidence = None, None, None
    try:
        variable_json = json.loads(variable_response)
        if "result" in variable_json:
            raw_result = str(variable_json["result"])
            result = raw_result.replace("\t", "")
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
    st.write(f"Result from AI: {result}")
    st.write(f"Evidence: {evidence}")
    st.write(f"Confidence level: {confidence_level}")
    st.write(f"Page number from AI: not support yet")
    submit_ai = st.button("Apply AI variable", )
    if submit_ai:
        with conn.session as s:
            sql = sqlalchemy.sql.text(
                'insert or replace into label(doc_id, variable, label, ai_label, manual_label, prompt_version) '
                'values (:doc_id, :variable, :label, :ai_label, :manual_label, :prompt_version)')
            s.execute(sql, params=dict(doc_id=st.session_state['doc_id_selection'],
                                       variable=variable_selection,
                                       label=result,
                                       ai_label=result,
                                       manual_label="",
                                       prompt_version="prompt version"))
            s.commit()

    st.subheader("Manual labeling area")
    select_existed_label = 'select existed label'
    input_label_manually = 'input label manually'
    use_existed_label = st.radio("Input label style", [input_label_manually, select_existed_label], index=0)
    if use_existed_label == select_existed_label:
        with st.form("select existed label"):
            existed = conn.query(f"select label from label where variable = '{variable_selection}'", ttl=0)
            existed_label_value = st.selectbox("Select label:", existed['label'].to_list(), index=None)
            submitted = st.form_submit_button("Apply manual variable")
            if submitted:
                with conn.session as s:
                    sql = sqlalchemy.sql.text(
                        'insert or replace into label(doc_id, variable, label, ai_label, manual_label, prompt_version) '
                        'values (:doc_id, :variable, :label, :ai_label, :manual_label, :prompt_version)')
                    s.execute(sql, params=dict(doc_id=st.session_state['doc_id_selection'],
                                               variable=variable_selection,
                                               label=existed_label_value,
                                               ai_label=result,
                                               manual_label=existed_label_value,
                                               prompt_version="prompt version"))
                    s.commit()
    else:
        with st.form("input form"):
            manual_variable_input = st.text_input("Input label:")
            submitted = st.form_submit_button("Apply input variable")
            if submitted:
                with conn.session as s:
                    sql = sqlalchemy.sql.text(
                        'insert or replace into label(doc_id, variable, label, ai_label, manual_label, prompt_version) '
                        'values (:doc_id, :variable, :label, :ai_label, :manual_label, :prompt_version)')
                    s.execute(sql, params=dict(doc_id=st.session_state['doc_id_selection'],
                                               variable=variable_selection,
                                               label=manual_variable_input,
                                               ai_label=result,
                                               manual_label=manual_variable_input,
                                               prompt_version="prompt version"))
                    s.commit()
    doc_id = st.session_state['doc_id_selection']
    current_pdf_csv = conn.query(f"select doc_id, variable, label from label where doc_id = '{doc_id}'", ttl=0)
    st.write(current_pdf_csv)


@st.fragment
def labeling_area():
    st.subheader("AI labeling area")
    variable_selection = st.selectbox("Select a Variable:", chain_dict.keys(), index=None, key=variable_select_box_key)
    if variable_selection:
        query = chain_dict[variable_selection]
        query = util.query_add_md(query)
        variable_response = str(openai_service.chat_with_pdf(pdf_path, query))
        logging.info(variable_response)
        st.session_state['variable_response'] = variable_response
        st.session_state['variable_selection'] = variable_selection
        submit_label()


@st.fragment
def summary_area(summary, height):
    st.text_area(f"Summary of {st.session_state['doc_id_selection']}: ", summary, int(height/2))

if doc_id_selection:
    filename = pdf_dict[st.session_state['doc_id_selection']]
    pdf_path = os.path.join('resources/pdf', filename)
    summary = openai_service.chat_with_pdf(pdf_path, summary_prompt)
    if not st.session_state['binary']:
        with (st.spinner('Reading file, calling Grobid...')):
            with open(pdf_path, 'rb') as f:
                binary = f.read()
                tmp_file = NamedTemporaryFile(delete=False)
                tmp_file.write(bytearray(binary))
                tmp_file.close()
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
            summary_area(summary, height)
        with col2:
            xml_filename = f'{filename[:-4]}.grobid.tei.xml'
            if not os.path.exists(os.path.join('resources/xml', xml_filename)):
                init_grobid().process_pdf_to_xml("resources/pdf", "resources/xml")
            export_pdf_body()
            export_pdf_selected_content()
            export_pdf_selected_content_as_txt()
            export_label_csv()
            export_log_csv()
            labeling_area()
