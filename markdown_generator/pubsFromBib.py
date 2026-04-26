#!/usr/bin/env python
# coding: utf-8

# # Publications markdown generator for academicpages
# 
# Takes a set of bibtex of publications and converts them for use with [academicpages.github.io](academicpages.github.io). This is an interactive Jupyter notebook ([see more info here](http://jupyter-notebook-beginner-guide.readthedocs.io/en/latest/what_is_jupyter.html)). 
# 
# The core python code is also in `pubsFromBibs.py`. 
# Run either from the `markdown_generator` folder after replacing updating the publist dictionary with:
# * bib file names
# * specific venue keys based on your bib file preferences
# * any specific pre-text for specific files
# * Collection Name (future feature)
# 
# TODO: Make this work with other databases of citations, 
# TODO: Merge this with the existing TSV parsing solution


from pybtex.database.input import bibtex
import pybtex.database.input.bibtex 
from time import strptime
import string
import html
import os
import re

#todo: incorporate different collection types rather than a catch all publications, requires other changes to template
publist = {
    "publication": {
        "file" : "publications.bib",
        "venuekey": "journal",
        "venue-pretext": "",
        "collection" : {"name":"publications",
                        "permalink":"/publication/"}
    }
}

html_escape_table = {
    "&": "&amp;",
    '"': "&quot;",
    "'": "&apos;"
    }

def html_escape(text):
    """Produce entities within text."""
    return "".join(html_escape_table.get(c,c) for c in text)


def clean_bibtex(text):
    """Convert BibTeX escaped characters to Unicode"""
    # Common BibTeX escapes - order matters (longer patterns first)
    replacements = [
        # Lowercase with umlauts
        (r'{\"u}', 'ü'), (r'{\-"u}', 'ü'), (r'{\"o}', 'ö'), (r'{\"a}', 'ä'),
        (r'{\ s}', 'ß'), (r'{\ss}', 'ß'),
        # Uppercase
        (r'{\"U}', 'Ü'), (r'{\"O}', 'Ö'), (r'{\"A}', 'Ä'),
        # Accented
        (r"{\'a}", 'á'), (r"{\'e}", 'é'), (r"{\'i}", 'í'), (r"{\'o}", 'ó'), (r"{\'u}", 'ú'),
        (r'{\`a}', 'à'), (r'{\`e}', 'è'), (r'{\`i}', 'ì'), (r'{\`o}', 'ò'), (r'{\`u}', 'ù'),
        # Other letters
        (r'{\c{C}}', 'Ç'), (r'{\c{c}}', 'ç'),
        (r'{\~n}', 'ñ'), (r'{\~a}', 'ã'), (r'{\~o}', 'õ'),
        (r'{\.z}', 'ż'), (r'{\.a}', 'ą'),
        (r'{\i}', 'ı'), (r'{\\i}', 'ı'),
        # Ligatures
        (r'{ff}', 'ff'), (r'{fi}', 'fi'), (r'{fl}', 'fl'), 
        (r'{ffi}', 'ffi'), (r'{ffl}', 'ffl'),
        # Dashes
        ('--', '–'), ('---', '—'),
    ]
    result = text
    for pattern, replacement in replacements:
        result = result.replace(pattern, replacement)
    # Remove remaining braces
    result = result.replace('{', '').replace('}', '')
    return result


def escape_yaml_string(text):
    """Escape string for YAML - avoid HTML entities breaking YAML"""
    # Replace quotes that could break YAML
    return text.replace('"', '\\"').replace("'", "\\'")


for pubsource in publist:
    parser = bibtex.Parser()
    bibdata = parser.parse_file(publist[pubsource]["file"])

    #loop through the individual references in a given bibtex file
    for bib_id in bibdata.entries:
        #reset default date
        pub_year = "1900"
        pub_month = "01"
        pub_day = "01"
        
        b = bibdata.entries[bib_id].fields
        
        try:
            pub_year = f'{b["year"]}'

            #todo: this hack for month and day needs some cleanup
            if "month" in b.keys(): 
                if(len(b["month"])<3):
                    pub_month = "0"+b["month"]
                    pub_month = pub_month[-2:]
                elif(b["month"] not in range(12)):
                    tmnth = strptime(b["month"][:3],'%b').tm_mon   
                    pub_month = "{:02d}".format(tmnth) 
                else:
                    pub_month = str(b["month"])
            if "day" in b.keys(): 
                pub_day = str(b["day"])

                
            pub_date = pub_year+"-"+pub_month+"-"+pub_day
            
            #strip out {} as needed (some bibtex entries that maintain formatting)
            clean_title = clean_bibtex(b["title"]).replace(" ","-")    

            url_slug = re.sub("\[.*\]|[^a-zA-Z0-9_-]", "", clean_title)
            url_slug = url_slug.replace("--","-")

            md_filename = (str(pub_date) + "-" + url_slug + ".md").replace("--","-")
            html_filename = (str(pub_date) + "-" + url_slug).replace("--","-")

            #Build Citation from text
            citation = ""

#citation authors - full name format: First Last
            authors_list = []
            for author in bibdata.entries[bib_id].persons["author"]:
                raw_first = author.first_names[0] if author.first_names else ""
                raw_last = author.last_names[0] if author.last_names else ""
                first = clean_bibtex(raw_first)
                last = clean_bibtex(raw_last)
                authors_list.append(first + " " + last)
            
            citation = ", ".join(authors_list) + ". "

            #citation title - with period outside italics
            title = clean_bibtex(b["title"])
            citation = citation + "*" + title + ".* "

            #add venue logic depending on citation type
            # For @inproceedings, use booktitle; for @article, use journal
            venue = ""
            if "booktitle" in b.keys():
                venue = clean_bibtex(b["booktitle"])
            elif "journal" in b.keys():
                venue = clean_bibtex(b["journal"])

            if venue:
                citation = citation + venue + " "
            
            citation = citation + "(" + pub_year + ")."
            
            # Escape for YAML
            citation_yaml = escape_yaml_string(citation)

            
            ## YAML variables - escape properly for YAML
            title_yaml = clean_bibtex(b["title"])
            md = "---\ntitle: \""   + title_yaml + '"' + "\n"
            
            md += """collection: """ +  publist[pubsource]["collection"]["name"]

            md += """\npermalink: """ + publist[pubsource]["collection"]["permalink"]  + html_filename
            
            note = False
            if "note" in b.keys():
                if len(str(b["note"])) > 5:
                    md += "\nexcerpt: \"" + clean_bibtex(b["note"]) + "\""
                    note = True

            md += "\ndate: " + str(pub_date) 

            md += "\nvenue: \"" +venue + "\""

            # Determine publication type: arXiv vs published
            # arXiv only if journal field contains "arXiv preprint"
            # All others (including workshop papers) are "published"
            pub_type = "published"
            if "journal" in b.keys() and "arXiv" in clean_bibtex(b["journal"]):
                pub_type = "arxiv"
            md += "\ntype: '" + pub_type + "'"
            
            url = False
            if "url" in b.keys():
                if len(str(b["url"])) > 5:
                    md += "\npaperurl: '" + b["url"] + "'"
                    url = True
            elif "doi" in b.keys():
                doi = clean_bibtex(b["doi"])
                if len(doi) > 5:
                    if not doi.startswith("http"):
                        doi = "https://doi.org/" + doi
                    md += "\npaperurl: '" + doi + "'"
                    url = True
            elif "journal" in b.keys() and "arXiv" in clean_bibtex(b["journal"]):
                arxiv_id = clean_bibtex(b["journal"])
                match = re.search(r'arXiv:([0-9.]+)', arxiv_id)
                if match:
                    arxiv_url = "https://arxiv.org/abs/" + match.group(1)
                    md += "\npaperurl: '" + arxiv_url + "'"
                    url = True

            md += "\ncitation: \"" + citation + "\""

            md += "\n---"

            
            ## Markdown description for individual page
            if note:
                md += "\n" + html_escape(clean_bibtex(b["note"])) + "\n"

            if url:
                paper_url = b.get("url", "")
                if not paper_url and "doi" in b.keys():
                    paper_url = "https://doi.org/" + clean_bibtex(b["doi"])
                elif not paper_url and "journal" in b.keys() and "arXiv" in clean_bibtex(b["journal"]):
                    arxiv_id = clean_bibtex(b["journal"])
                    match = re.search(r'arXiv:([0-9.]+)', arxiv_id)
                    if match:
                        paper_url = "https://arxiv.org/abs/" + match.group(1)
                md += "\n[Access paper here](" + paper_url + "){:target=\"_blank\"}\n" 
            else:
                md += "\nUse [Google Scholar](https://scholar.google.com/scholar?q="+html.escape(clean_title.replace("-","+"))+"){:target=\"_blank\"} for full citation"

            md_filename = os.path.basename(md_filename)

            try:
                with open("../_publications/" + md_filename, 'w') as f:
                    f.write(md)
                print(f'SUCESSFULLY PARSED {bib_id}: "', b["title"][:60],"..."*(len(b['title'])>60),"\"")
            except IOError as e:
                print(f'ERROR writing file for {bib_id}: {e}')

        except KeyError as e:
            print(f'WARNING Missing Expected Field {e} from entry {bib_id}: "', b.get("title", "")[:30],"...\"")
            continue