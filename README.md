# Action Editor Search

During the TMLR submission process, authors must suggest at least three action editors to handle their paper. This script helps authors find relevant AEs. Starting from the papers in your .bib file, it will use the Semantic Scholar API to perform a breadth-first search through the citation graph, identifying papers authored by the journal's action editors.

## Getting Started

### Prerequisites

- Python 3.x
- An API key for Semantic Scholar, [request a key here](https://www.semanticscholar.org/product/api#api-key-form).

### Installation

1. Clone this repository:
   ```
   git clone https://github.com/JeremyIV/action-editor-search.git
   ```
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set your Semantic Scholar API key as an environment variable:
   ```
   export S2_API_KEY='your_api_key_here'
   ```

### Usage

Run the script by specifying the path to your paper's `.bib` file, and optionally the depth for the BFS:

```
python search.py path/to/your/bibliography.bib --depth=1
```

Be warned that this script takes a long time to run, and the runtime increases ~exponentially with the depth. It prints a report of its findings to stdout, consider piping to `tee` for a more persistent output.

#### Arguments

- `bibfile`: Path to your `.bib` file.
- `--editors_url`: URL to the action editors webpage. Default is `https://jmlr.org/tmlr/editorial-board.html`.
- `--depth`: Depth to which to perform the citation graph BFS. Depth=0 simply checks if any of the papers in your bibliography were authored by action editors. Depth=1 additionally checks papers which cited/were cited by the papers in your bibliography. Runtime increases exponentially with the depth, so depth=2 can take a very long time. Higher depths are probably impractical and also irrelevant.
