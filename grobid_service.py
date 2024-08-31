from grobid_client.grobid_client import GrobidClient

# docker run --rm --init --ulimit core=0 -p 8070:8070 lfoppiano/grobid:0.8.0
if __name__ == "__main__":
    client = GrobidClient(config_path="./grobid_config.json")
    client.process("processFulltextDocument", "./resources/test_pdf/", output="./resources/test_out/", consolidate_citations=True, tei_coordinates=True, force=True)