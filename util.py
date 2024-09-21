from bs4 import BeautifulSoup

def query_add_md(q: str):
    if not q.endswith('.') or not q.endswith('?'):
        q = q + '.'
    return q + "save the result in a json format, the keys are result, your confidence level(high/middle/low), and evidence."


if __name__ == '__main__':
    with open('resources/xml/10.1177&107769908105800204.grobid.tei.xml') as f:
        soup = BeautifulSoup(f, features="xml")
        # for paragraph in soup.find_all('p'):
        #     print(paragraph.text)
        print(soup.title.text)
        for author in soup.find_all('author'):
            if author.persName:
                personName = ''
                for name in author.persName.children:
                    personName = personName + name.text + " "
                print(personName)
        for figure in soup.find_all('figure'):
            if figure.head:
                print(figure.head.text)
