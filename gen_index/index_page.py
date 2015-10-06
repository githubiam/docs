link_template="""\
   <ul>
      <li><a href="{lang_code:}/overview/tokenization.html">Tokenization</a></li>
      <li>Morphology
        <ul>
          <li><a href="{lang_code:}/overview/morphology.html">General principles</a></li>
          <li><a href="{lang_code:}/pos/index.html">{lang_name:} POS tags</a> (<a href="{lang_code:}/pos/all.html">single document</a>)</li>
          <li><a href="{lang_code:}/feat/index.html">{lang_name:} features</a> (<a href="{lang_code:}/feat/all.html">single document</a>)</li>
        </ul>
      </li>
      <li>Syntax
        <ul>
          <li><a href="{lang_code:}/overview/syntax.html">General principles</a></li>
          <li><a href="{lang_code:}/overview/specific-syntax.html">Specific constructions</a></li>
          <li><a href="{lang_code:}/dep/index.html">{lang_name:} relations</a> (<a href="{lang_code:}/dep/all.html">single document</a>)</li>
        </ul>
      </li>
    </ul>
"""

import sys
import glob
import os.path
import json
import re
import codecs
import StringIO

no_data_token_count_span="""<span class="widespan" style="color:gray"><span class="hint--top hint--info" data-hint="No corpus data">-</span></span>"""
token_count_span="""<span class="widespan"><span class="hint--top hint--info" data-hint="{token_count:,} tokens {word_count:,} words {tree_count:,} sentences">{tcountk:,}K</span></span>"""
def get_token_count_span(corpus_data):
    token_count=corpus_data.get("token_count",0)
    if token_count==0: #No data
        return no_data_token_count_span
    else:
        return token_count_span.format(tcountk=token_count//1000,**corpus_data)


def get_column_icons(corpus_data):
    r="""<span class="widespan">"""
    if corpus_data.get("words_with_lemma_count",0)>0:
        r+="""<span class="tagspan"><span class="hint--top hint--info" data-hint="Lemmas">&#9409;</span></span>"""
    else:
        r+="""<span class="tagspan"></span>"""
    if corpus_data.get("catvals",0)>0:
        r+="""<span class="tagspan"><span class="hint--top hint--info" data-hint="Features">&#9403;</span></span>"""
    else:
        r+="""<span class="tagspan"></span>"""
    if corpus_data.get("words_with_deps_count",0)>0:
        r+="""<span class="tagspan"><span class="hint--top hint--info" data-hint="Secondary dependencies">&#9401;</span></span>"""
    else:
        r+="""<span class="tagspan"></span>"""
    r+="""</span>"""
    return r

categories={(u"Documentation status",u"stub"):"""<span class="widespan" style="color:gray"><span class="hint--top hint--info" data-hint="No documentation">-</span></span>""",
            (u"Documentation status",u"partial"):"""<span class="widespan"><span class="hint--top hint--info" data-hint="Partial documentation"><i class="fa fa-file-o"></i></span></span>""",
            (u"Documentation status",u"complete"):"""<span class="widespan"><span class="hint--top hint--info" data-hint="Complete documentation"><i class="fa fa-file-text-o"></i></span></span>""",
            (u"Data source",u"unknown"):"""<span class="widespan"><span class="hint--top hint--info" data-hint="Data source not known">-</span></span>""",
            (u"Data source",u"automatic conversion"):"""<span class="widespan"><span class="hint--top hint--info" data-hint="Automatic conversion"><i class="fa fa-cogs"></i></span></span>""",
            (u"Data source",u"automatic conversion + manual check"):"""<span class="widespan"><span class="hint--top hint--info" data-hint="Automatic conversion with manual corrections"><i class="fa fa-cogs"></i><!--<i class="fa fa-plus" style="font-size: 0.75em; line-height: 1.33em; vertical-align: +10%;">--><i class="fa fa-check"></i></span></span>""",
            (u"Data source",u"native UD annotation"):"""<span class="widespan"><span class="hint--top hint--info" data-hint="Manual annotation"><i class="fa fa-user"></i></span></span>""",
            (u"License",u"none"):"""<span class="widespan"><span class="hint--top hint--info" data-hint="License not known">-</span></span>""",
            (u"Data available since",u"UD v1.0"):"""<span class="widespan"><span class="hint--top hint--info" data-hint="First released in UD version 1.0 (Jan 2015)"><i class="fa fa-check"></i></span></span>""",
            (u"Data available since",u"UD v1.1"):"""<span class="widespan"><span class="hint--top hint--info" data-hint="First released in UD version 1.1 (May 2015)"><i class="fa fa-check"></i></span></span>""",
            (u"Data available since",u"UD v1.2"):"""<span class="widespan"><span class="hint--top hint--info" data-hint="Will be released in UD version 1.2 (November 2015)"><i class="fa fa-hourglass-end"></i></span></span>""",
            (u"Data available since",u"none"):"""<span class="widespan"><span class="hint--top hint--info" data-hint="No firm schedule for data release">-</span></span>"""}

license_span="""<span class="widespan"><span class="hint--top hint--info" data-hint="{license:}">{licenseshort:}</span></span>"""
for lic in ("CC BY-NC-SA 3.0","CC BY-NC-SA 3.0 US","CC BY-NC-SA 4.0"):
    categories[(u"License",lic)]=license_span.format(license=lic,licenseshort="""<img class="license"  src="logos/by-nc-sa.svg">""")
for lic in ("GNU GPL Version 2",):
    categories[(u"License",lic)]=license_span.format(license=lic,licenseshort="""<img class="license" src="logos/gpl.svg">""")
for lic in ("CC BY-SA 4.0","CC BY-SA 3.0"):
    categories[(u"License",lic)]=license_span.format(license=lic,licenseshort="""<img class="license" src="logos/by-sa.svg">""")
for lic in ("CC BY 4.0",):
    categories[(u"License",lic)]=license_span.format(license=lic,licenseshort="""<img class="license" src="logos/by.svg">""")

valueRe=re.compile(u"^([a-zA-Z ]+): ([A-Za-z0-9+. -]+)$")
def analyze_readme(dir_name):
    readme_data={u"Documentation status":u"stub",u"Data source":u"unknown",u"License":u"none",u"Data available since":u"none"}
    readmes=sorted(x for x in glob.glob(os.path.join(dir_name,"*")) if "readme" in x.lower())
    if not readmes: #No readme file!
        return readme_data
    with codecs.open(readmes[0],"r","utf-8") as f:
        for line in f:
            match=valueRe.match(line)
            if match: #Maybe one of our values?
                cat,val=match.group(1).strip(),match.group(2).strip()
                if (cat,val) in categories:
                    #Yes! this is a known category, we have a perfect match
                    readme_data[cat]=val
    return readme_data
                
def get_language_span(l):
    return """<span class="widespan">{}</span>""".format(l)

flags=json.loads(open("flags.json").read())
def get_flag_span(lang_name):
    ccode=flags.get(lang_name)
    if ccode:
        return """<span class="flagspan"><img class="flag" src="flags/svg/{}.svg"></span>""".format(ccode)
    else:
        return """<span class="flagspan"> </span>"""

lcodes=json.loads(open("lcodes.json").read())

def gen_table(args):
    
    a_data=StringIO.StringIO()
    # Will create a line for every language which has a repository
    langs=sorted(os.path.basename(x).replace(".json","") for x in glob.glob("_corpus_data/*.json"))
    for l in langs:
        with open(os.path.join("_corpus_data",l+".json"),"r") as f:
            corpus_data=json.load(f)
        corpus_data[u"lang_code"]=lcodes[l]
        corpus_data[u"lang_name"]=l
        print >> a_data, "<div>"
        print >> a_data, get_flag_span(l)
        print >> a_data, get_language_span(l)
        print >> a_data, get_token_count_span(corpus_data)
        print >> a_data, get_column_icons(corpus_data)
        readme_data=analyze_readme(os.path.join(args.ud_data,"UD_"+l))
        print >> sys.stderr, l
        for c in (u"Documentation status", u"Data source", u"Data available since", u"License"):
            print >> a_data, categories[c,readme_data[c]]
        print >> a_data, "</div>"
        print >> a_data, "<div>"
        print >> a_data, link_template.format(**corpus_data)
        print >> a_data, "</div>"
    return a_data

if __name__=="__main__":
    import argparse
    parser = argparse.ArgumentParser(description='generates the index page')
    parser.add_argument('--ud-data', required=True, help='Where is the UD data, so I can grab the readmes? (DIRECTORY)')
    args = parser.parse_args()
    
    a_data=gen_table(args)
    with codecs.open("index.template","r","utf-8") as f:
        index=f.read().replace("CONTENTSGOESHERE",a_data.getvalue())
        print index