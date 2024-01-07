import requests
import json
import pandas as pd
import webbrowser
import tempfile
import argparse
import os
import logging
from typing import NamedTuple
import dotenv
from functools import partial
import sys


HTML_DOCUMENT_TITLE = 'GitHub Repo Size'

# This stylesheet is a slightly modified version of
# https://github.com/jupyter/notebook/blob/b8b66332e2023e83d2ee04f83d8814f567e01a4e/notebook/static/notebook/less/renderedhtml.less
LESS_STYLESHEET = """
.rendered_html {
    
    color: @text-color;
    em {font-style: italic;}
    strong {font-weight: bold;}
    u {text-decoration: underline;}
    :link {text-decoration: underline;}
    :visited {text-decoration: underline;}

    // For a 14px base font size this goes as:
    // font-size = 26, 22, 18, 14, 12, 12
    // margin-top = 14, 14, 14, 14, 8, 8
    h1 {font-size: 185.7%; margin: 1.08em 0 0 0; font-weight: bold; line-height: 1.0;}
    h2 {font-size: 157.1%; margin: 1.27em 0 0 0; font-weight: bold; line-height: 1.0;}
    h3 {font-size: 128.6%; margin: 1.55em 0 0 0; font-weight: bold; line-height: 1.0;}
    h4 {font-size: 100%; margin: 2em 0 0 0; font-weight: bold; line-height: 1.0;}
    h5 {font-size: 100%; margin: 2em 0 0 0; font-weight: bold; line-height: 1.0; font-style: italic;}
    h6 {font-size: 100%; margin: 2em 0 0 0; font-weight: bold; line-height: 1.0; font-style: italic;}

    // Reduce the top margins by 14px compared to above
    h1:first-child {margin-top: 0.538em;}
    h2:first-child {margin-top: 0.636em;}
    h3:first-child {margin-top: 0.777em;}
    h4:first-child {margin-top: 1em;}
    h5:first-child {margin-top: 1em;}
    h6:first-child {margin-top: 1em;}

    ul:not(.list-inline),
    ol:not(.list-inline) {padding-left: 2em;}
    ul {list-style:disc;}
    ul ul {
      list-style:square;
      margin-top: 0;
    }
    ul ul ul {list-style:circle;}
    ol {list-style:decimal;}
    ol ol {
      list-style:upper-alpha; 
      margin-top: 0;
    }
    ol ol ol {list-style:lower-alpha; }
    ol ol ol ol {list-style:lower-roman; }
    /* any extras will just be numbers: */
    ol ol ol ol ol {list-style:decimal;}
    * + ul {margin-top: 1em;}
    * + ol {margin-top: 1em;}

    hr {
        color: @rendered_html_border_color;
        background-color: @rendered_html_border_color;
    }

    pre {
        margin: 1em 2em;
        padding: 0px;
        background-color: @body-bg;
    }

    code {
        background-color: #eff0f1;
    }

    p code {
        padding: 1px 5px;
    }

    pre code {background-color: @body-bg;}

    pre, code {
        border: 0;
        color: @text-color;
        font-size: 100%;
    }

    blockquote {margin: 1em 2em;}

    table {
        border: none;
        border-collapse: collapse;
        border-spacing: 0;
        color: @rendered_html_border_color;
        font-size: 16px;
        table-layout: fixed;
    }
    thead {
        border-bottom: 1px solid @rendered_html_border_color;
        vertical-align: bottom;
    }
    tr, th, td {
        text-align: right;
        vertical-align: middle;
        padding: 0.5em 0.5em;
        line-height: normal;
        white-space: normal;
        max-width: none;
        border: none;
    }
    th {
        font-weight: bold;
    }
    tbody tr:nth-child(odd) {
        background: #2a2a2a;  // this is the color of the even rows 
    }
    tbody tr:hover {
        background: rgba(66, 165, 245, 0.2);
    }
    * + table {margin-top: 1em;}

    p {text-align: left;}
    * + p {margin-top: 1em;}

    img {
        display: block;
        margin-left: auto;
        margin-right: auto;
    }
    * + img {margin-top: 1em;}
    
    img, svg {
        max-width: 100%;
        height: auto;
        &.unconfined {
            max-width: none;
        }
    }

    // Override bootstrap settings, see #1390
    .alert {margin-bottom: initial;}
    * + .alert {margin-top: 1em;}
}

[dir="rtl"] .rendered_html {
    p {
        text-align : right;
    }
}
"""


# The style block that's needed, including defining the necessary LESS variables and the js script to render the LESS directly in the browser (no need to precompile to CSS)
LESS_STYLESHEET_BLOCK = """
<style type="text/less">
	// Define the LESS variables
	@text-color: #fff; // No effect
	@body-bg: #fff; // No effect
	@rendered_html_border_color: #fff; // (white) the default color of text in the table and the line below the table header

	%(less)s

</style>
<script src="https://cdnjs.cloudflare.com/ajax/libs/less.js/4.1.3/less.min.js"></script>	
""" % {"less": LESS_STYLESHEET}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>

    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>%(doc_title)s</title>

    <style>
		body {
			background-color: #202020; // page background and odd rows of the table
			font-size: 16px;
			color: #fff;
		}
	</style>

	%(less_stylesheet_block)s
</head>
<body>
    <div class="rendered_html">
        %(content)s
    </div>
</body>
</html>
""" % {'doc_title': HTML_DOCUMENT_TITLE, 'less_stylesheet_block': LESS_STYLESHEET_BLOCK, 'content': '|TABLE|'} 


class Data(NamedTuple):
	institution: str
	repo: str
	size_gb: float



def inst_and_repo_as_tuple(url: str) -> tuple[str, str]|None:
	try:
		return ( (tok:=url.split('/'))[-2], tok[-1].split('.')[0] )
	except IndexError:
		logging.warning(f'Failed to parse {url}; expected a URL of the form https://github.com/xxx/yyy.git. Skipping.')
		return None

def repo_list_to_pairs(repo_list: list[str]) -> list[tuple[str, str]]:
	#return [(t:=inst_and_repo_as_tuple(repo)) for repo in repo_list if t is not None] # walrus doesn't seem to work in list comprehensions
	return [inst_and_repo_as_tuple(repo) for repo in repo_list if inst_and_repo_as_tuple(repo) is not None]


# highlight rows of items in repos
def highlight(row: pd.Series, repo_list: list[str]) -> list[str]:
	if (row.institution, row.repo) in repo_list_to_pairs(repo_list=repo_list):
		return ['color: gray']*len(row)
	else:
		return ['']*len(row)


ref_repos = [
	'https://github.com/jupyter/notebook.git',
	'https://github.com/tensorflow/tensorflow.git',
	'https://github.com/NixOS/nixpkgs.git',
	'https://github.com/apple/swift.git',
	'https://github.com/kubernetes/kubernetes.git',
	'https://github.com/microsoft/vscode.git',
	'https://github.com/freeCodeCamp/freeCodeCamp.git',
	'https://github.com/chromium/chromium.git'	
]

TOKEN_ENV_VAR_NAME = 'GITHUB_GENERAL_QUERIES_TOKEN'

GITHUB_API_URL = 'https://api.github.com/repos'

if __name__ == '__main__':
	dotenv.load_dotenv()
	
	print('GitHub Repo Size Collector')


	parser = argparse.ArgumentParser(description="GitHub Repo Size")
	parser.add_argument('repo_list', help='A space-separated list of GitHub repos of the form https://github.com/xxx/yyy.git or text files containing a list of repo (on per line).', nargs='*', default=[], metavar='REPOS')
	parser.add_argument('--no-ref-repos', help='Do not include the reference repos', action='store_true')

	args = parser.parse_args()

	try:
		token = os.getenv(TOKEN_ENV_VAR_NAME)
		if token is None:
			logging.warning(f'No {TOKEN_ENV_VAR_NAME} environment variable found (it can also be set in a .env file in the current directory). Proceeding with no authentication, but this will be rate-limited.')
			authentication_header = {}
		else:
			authentication_header = {'Authorization': f'Bearer {token}'}

		repos = []
		for repo in args.repo_list:
			if os.path.isfile(repo):
				with open(repo, 'r') as f:
					repos.extend([line.strip() for line in f.readlines() if line.strip()])
			else:
				repos.append(repo)

		if not repos:
			if args.no_ref_repos:
				logging.warning('No repos specified, nothing to do.')
				sys.exit()
			logging.warning('No repos specified, using the reference repos only.')

		if args.no_ref_repos:
			all_repos = repos
		else:
			all_repos = ref_repos + repos

		results: list[Data] = []
		# get the institution and repo names (e.g. langchain-ai, langchain) (without the .git)

		for p in repo_list_to_pairs(all_repos):
			# get the response from the API
			req = f'{GITHUB_API_URL}/{p[0]}/{p[1]}'
			if authentication_header:
				r = requests.get(req, headers=authentication_header)
			else:
				r = requests.get(req)

			if r.status_code != 200:
				logging.error(f'Failed to get repo info for {p[0]}/{p[1]}: {r.status_code}, {r.json()}')
				logging.warning(f'Skipping {p[0]}/{p[1]}')
				continue
			# get the size
			try:
				size = r.json()['size']
				results.append(Data(institution=p[0], repo=p[1], size_gb=size/1024/1024))
			except KeyError:
				logging.error(f'Failed to get size for {p[0]}/{p[1]}: {r.json()}')
				logging.warning(f'Skipping {p[0]}/{p[1]}')


		df = pd.DataFrame(results)
		# make the institution the index and sort descending by size
		df = df.sort_values(by='size_gb', ascending=False)

		# display the dataframe
		table_html = df.style.apply(partial(highlight, repo_list=ref_repos), axis=1).format(precision=2).hide(axis='index').to_html()

		html = HTML_TEMPLATE.replace('TABLE', table_html)

		# Save the HTML to a temporary file and open it in the browser
		with tempfile.NamedTemporaryFile('w', delete=False, suffix='.html') as f:
			f.write(html)
			webbrowser.open(f.name)

	except ValueError as e:
		logging.error(e)
		sys.exit()

	except Exception as e:
		logging.exception(e)
		sys.exit()