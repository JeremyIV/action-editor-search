# Action Editor Suggester

This script helps authors identify potential action editors for their JMLR/TMLR submissions by analyzing citation graphs derived from `.bib` files. Using the Semantic Scholar API, it performs a breadth-first search (BFS) through the citation graph starting from the citations within the provided `.bib` file, identifying papers authored by the journal's action editors.

## Getting Started

### Prerequisites

- Python 3.x
- An API key for Semantic Scholar, [request a key here](https://www.semanticscholar.org/product/api#api-key-form).

### Installation

1. Clone this repository:
   $
   git clone https://github.com/JeremyIV/action-editor-search.git
   $
2. Install the required dependencies:
   $
   pip install -r requirements.txt
   $
3. Set your Semantic Scholar API key as an environment variable:
   $
   export S2_API_KEY='your_api_key_here'
   $

### Usage

Run the script by specifying the path to your `.bib` file, and optionally, the URL to the action editors webpage and the depth for the BFS:

$
python <script-name>.py path/to/your/file.bib --editors_url=https://jmlr.org/tmlr/editorial-board.html --depth=2
$

#### Arguments

- `bibfile`: Path to your `.bib` file.
- `--editors_url`: URL to the action editors webpage. Default is `https://jmlr.org/tmlr/editorial-board.html`.
- `--depth`: Depth to which to perform the citation graph BFS. Default is `2`.

## Contributing

Contributions are welcome! Please feel free to submit a pull request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
