import requests
import re
import tqdm
from bs4 import BeautifulSoup
import argparse
import time
import os
import bibtexparser

#############################################
## CLASSES AND UTILITIES
#############################################

class Paper:
    def __init__(self, id, title):
        self.id = id
        self.title = title
        self.cited_paper = None
        self.referenced_by_paper = None
    
    def cited(self, paper):
        self.cited_paper = paper
    
    def referenced_by(self, paper):
        self.referenced_by_paper = paper

    def __str__(self):
        return f"Paper(id={self.id}, title='{self.title})'"
    
    def __repr__(self):
        return f"Paper(id={self.id}, title='{self.title})'"

    def get_path_string(self):
        path_string = f'"{self.title}"'
        if self.cited_paper:
            path_string += "\n    which cited " + self.cited_paper.get_path_string()
        elif self.referenced_by_paper:
            path_string += "\n    which was referenced by " + self.referenced_by_paper.get_path_string()
        
        return path_string
    
    def get_path_depth(self):
        if self.cited_paper:
            return 1 + self.cited_paper.get_path_depth()
        elif self.referenced_by_paper:
            return 1 + self.referenced_by_paper.get_path_depth()
        else:
            return 0
        

def fetch_citation_titles(bibfile):
    """
    Extracts citations from a given .bib file using bibtexparser.

    :param bibfile: A string path to the .bib file containing citation data.
    :return: A list of the titles of each paper in the bibfile.
    """
    
    with open(bibfile) as bibtex_file:
        bib_database = bibtexparser.load(bibtex_file)
        
    # Extract titles from each entry in the .bib file
    titles = [entry['title'] for entry in bib_database.entries]
    return titles

def request_with_retries(url, max_retries=4, session=None):
    """
    Send a request and retry on 429 status with exponential backoff.

    :param url: The URL to request.
    :param max_retries: Maximum number of retries.
    :param session: Optional requests session.
    :return: The response object.
    """
    if not session:  # Create a session if one wasn't provided
        session = requests.Session()
    wait_time = 1  # Initial wait time in seconds
    for attempt in range(max_retries):
        response = session.get(url)
        if response.status_code != 429:  # If not 'Too Many Requests', break the loop
            return response
        time.sleep(wait_time)
        wait_time *= 2  # Exponentially increase wait time
    
    # After exceeding max_retries, return the last response
    return response


def get_papers_on_s2(titles, session):
    """
    Retrieves DBLP IDs and titles for a list of paper titles and returns instances of Paper class.

    :param titles: A list of paper titles.
    :return: A list of Paper instances.
    """
    papers = []
    base_url = "https://api.semanticscholar.org/graph/v1/paper/search"

    for title in tqdm.tqdm(titles):
        cleaned_title = re.sub(r'[^a-zA-Z0-9 ]', '', title)
        query = '+'.join(cleaned_title.split())
        response = request_with_retries(f"{base_url}?query={query}&fields=title", session=session)

        if response.status_code == 200:
            result = response.json()
            if 'data' in result:
                if len(result['data']) > 0:
                    paper_id = result['data'][0]['paperId']
                    title = result['data'][0]['title']
                    papers.append(Paper(paper_id, title))
        else:
            print(f"HTTP error {response.status_code}")
    
    return papers

def get_openreview_url(editor):
    openreview_link = editor.find('a', text='OpenReview')
    return openreview_link['href'] if openreview_link else None

# Function to get the DBLP XML URL from an OpenReview page
def get_dblp_xml_url(openreview_url):
    response = requests.get(openreview_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    dblp_link = soup.find('a', text='DBLP')
    if dblp_link:
        dblp_pid = dblp_link['href']
        return dblp_link['href'] + '.xml'
    return None

# Function to parse publication titles and arXiv IDs from a DBLP XML URL
def get_publications_with_ids(dblp_xml_url):
    response = requests.get(dblp_xml_url)
    soup = BeautifulSoup(response.text, 'xml')
    publications = []
    for article in soup.find_all('article'):
        title = article.find('title').text
        ee = article.find('ee', type='oa')
        id_str = None
        if ee:
            if 'arxiv.org' in ee.text:
                arxiv_id = ee.text.split('/')[-1]
                id_str = f"ARXIV:{arxiv_id}"
            elif 'doi.org' in ee.text:
                # More robust extraction of the DOI, ensuring it works for various formats
                doi_id = ee.text.split('doi.org/')[1]
                id_str = f"DOI:{doi_id}"
        publications.append((title, id_str))
    return publications

# Adjusted main scraping function to use the new publications fetching function
def scrape_action_editor_publications(url):
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    action_editors_heading = soup.find('h3', text='TMLR Action Editors')
    action_editors_list = action_editors_heading.find_next_sibling('ul')
    action_editors = action_editors_list.find_all('li')

    editors_publications = []

    for editor in tqdm.tqdm(action_editors):
        editor_name = editor.find('a').text
        try:
            openreview_url = get_openreview_url(editor)
            if openreview_url:
                dblp_xml_url = get_dblp_xml_url(openreview_url)
                if dblp_xml_url:
                    publications = get_publications_with_ids(dblp_xml_url)
                    editors_publications.append((editor_name, publications))
                else:
                    editors_publications.append((editor_name, [("DBLP link not found", None)]))
            else:
                editors_publications.append((editor_name, [("OpenReview link not found", None)]))
        except Exception as e:
            print(f"Error processing {editor_name}: {e}")
            editors_publications.append((editor_name, [(f"Error: {e}", None)]))
    
    return editors_publications

def scrape_editors_paper_ids(url, s2_api_key):
    """
    Scrapes authors and their publication lists from a given URL, preferably OpenReview, and DBLP.

    :param url: The URL from which to scrape author information.
    :return: A dictionary mapping authors to their publication lists.
    """
    # a list of (editor_name, publications) pairs, where each publication is a (title, arxiv_id pair)
    print("Scraping for AE's publications")
    editors_publications = scrape_action_editor_publications(url)
    
    print("getting AE's publications' S2 Ids!")
    
    editors_paper_ids = {}
    for editor, publications in tqdm.tqdm(editors_publications):
        arxiv_ids = [id for title, id in publications[:500] if id]
        r = requests.post(
            'https://api.semanticscholar.org/graph/v1/paper/batch',
            params={'fields': 'title,paperId'},
            json={"ids": arxiv_ids},
            headers={'x-api-key': s2_api_key}
        )
        wait_time = 1
        while r.status_code == 429:
            time.sleep(wait_time)
            wait_time *= 2
            r = requests.post(
                'https://api.semanticscholar.org/graph/v1/paper/batch',
                params={'fields': 'title'},
                json={"ids": arxiv_ids},
                headers={'x-api-key': s2_api_key}
            )
            if wait_time > 10:
                break
        paper_ids = []
        if r.status_code == 200:
            data = r.json()
            for row in data:
                if row is not None and 'paperId' in row:
                    paper_ids.append(row['paperId'])
        if paper_ids:
            editors_paper_ids[editor] = paper_ids
    
    return editors_paper_ids

def get_citing_and_referenced_papers(paper_id, session):
    """
    Fetches the papers that cite and are referenced by the given paper.

    :param paper_id: The ID of the paper of interest.
    :return: Two lists, the first of citing papers' IDs and the second of referenced papers' IDs.
    """
    url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}/?fields=citations.paperId,citations.title,references.paperId,references.title"
    response = request_with_retries(url, session=session)
    if response and response.status_code == 200:
        data = response.json()
        citing_papers = [Paper(c['paperId'], c['title']) for c in data.get('citations', [])]
        referenced_papers = [Paper(r['paperId'], r['title']) for r in data.get('references', [])]
        return citing_papers, referenced_papers
    else:
        return [], []  # Return empty lists if the request fails or if there's no data

def printFinding(editor, paper):
    print(f"{editor} authored {paper.get_path_string()}")

def printFindings(findings):
    for author, papers in findings.items():
        print(f"{author} authored:")
        for paper in papers:
            print("  " + paper.get_path_string())
            
def check_papers(papers, editors_paper_ids, findings):
    for editor, editor_paper_ids in editors_paper_ids.items():
        editor_paper_ids = set(editor_paper_ids)
        for paper in papers:
            if paper.id in editor_paper_ids:
                printFinding(editor, paper)
                if editor not in findings:
                    findings[editor] = []
                findings[editor].append(paper)

def main():
    ################################################
    ## Script inputs
    ################################################

    parser = argparse.ArgumentParser(description='''
    Suggest action editors for your paper from your .bib file.

    Performs a BFS through the citation graph from the papers in your .bib file, and finds papers
    authored by action editors.
    ''')

    parser.add_argument("bibfile", type=str, help="Path to your .bib file")
    parser.add_argument("--editors_url", type=str, default="https://jmlr.org/tmlr/editorial-board.html", help="URL to the action editors webpage.")
    parser.add_argument("--depth", type=int, default=2, help="Depth to which to perform the citation graph BFS.")

    args = parser.parse_args()

    s2_api_key = os.getenv('S2_API_KEY')

    if s2_api_key is None:
        print("You must set the environment variable S2_API_KEY to your Semantic Scholar API key to run this script. To request an API key, go here: https://www.semanticscholar.org/product/api#api-key-form")
        exit(1)

    session = requests.Session()
    session.headers.update(
        {'x-api-key': s2_api_key})

    #########################################################
    ## Main script
    #########################################################

    print(f"Parsing {args.bibfile}...")
    citations = fetch_citation_titles(args.bibfile)
    print(f"Looking up citations on Semantic Scholar...")
    papers = get_papers_on_s2(citations, session)

    print(f"Scraping authors' publications from {args.editors_url}")
    editors_paper_ids = scrape_editors_paper_ids(args.editors_url, s2_api_key)

    findings = {}

    print("Beginning BFS...")

    check_papers(papers, editors_paper_ids, findings)
                    
    fringe = list(papers)
    found_ids = set(paper.id for paper in papers)

    while fringe:
        try:
            paper = fringe.pop(0)
            
            if paper.get_path_depth() > args.depth:
                break
                
            citing_papers, referenced_papers = get_citing_and_referenced_papers(paper.id, session)

            new_papers = []

            for citing_paper in citing_papers:
                if citing_paper.id not in found_ids:
                    found_ids.add(citing_paper.id)
                    citing_paper.cited(paper)
                    new_papers.append(citing_paper)

            for referenced_paper in referenced_papers:
                if referenced_paper.id not in found_ids:
                    found_ids.add(referenced_paper.id)
                    referenced_paper.referenced_by(paper)
                    new_papers.append(referenced_paper)

            fringe.extend(new_papers)
            check_papers(new_papers, editors_paper_ids, findings)
        except KeyboardInterrupt:
            print(f"Keyboard interrupt, stopping BFS")
            break

    print(f"{len(found_ids)} papers searched in BFS")
    printFindings(findings)

if __name__ == "__main__":
    main()