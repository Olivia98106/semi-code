## Usuage 

1. download the project
2. load dependencies in `requirements.txt`
3. add an .env with your OPENAI_API_KEY=xxx
4. docker run --rm --init --ulimit core=0 -p 8070:8070 lfoppiano/grobid:0.8.0
5. streamlit run streamlit_app_b.py
6. streamlit run streamlit_app_c.py --server.port 8502
7. if you want to upload pdf file, copy the file and paste under `resources/pdf` folder, also insert the doc_id and filename in table `pdf` in database