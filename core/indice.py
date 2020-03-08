import os
import yaml
from .web import Web
import sys
import bs4
from bunch import Bunch
import json
import re

re_sp = re.compile(r"\s+")

def read_yml(fl):
    with open(fl, "r") as f:
        return yaml.load(f, Loader=yaml.FullLoader)

def write(f, margin, key, value):
    if value is None:
        value="null"
    else:
        value = '"'+value+'"'
    f.write(margin)
    f.write(key+": ")
    f.write(value)
    f.write("\n")

def build_indice_from_local(cnf):
    if not os.path.isfile(cnf.html):
        return False
    with open(cnf.html, "r") as f:
        soup = bs4.BeautifulSoup(f.read(), "lxml")
    for a in soup.select("article[data-src]"):
        a.extract()
    items=[]
    for h in soup.findAll(["h1", "h2", "h3", "h4", "h5", "h6"]):
        l = int(h.name[1:])-1
        a = h.find("a", text="#")
        if a:
            a.extract()
            a = a.attrs["href"]
        h = re_sp.sub(" ", h.get_text()).strip()
        if l>0 and len(items)>0:
            pre = items[len(items)-1]
            if pre.level<l:
                pre.children = True
        items.append(Bunch(
            title=h,
            url=a,
            level=l,
            children=False
        ))
    if not items:
        return False
    with open(cnf.indice, "w") as f:
        for i in items:
            margin = "  "*i.level
            write(f, margin, "- titulo", i.title)
            margin = margin + "  "
            write(f, margin, "url", i.url)
            if i.children:
                f.write(margin+"hijos:\n")
    cnf.indice = read_yml(cnf.indice)
    return True

def build_indice_from_web(cnf):
    wp = MareaSpider(cnf)
    if wp.error:
        print("#"+str(cnf.num),"<", error, "[No se pudo generar %s]" % cnf.indice)
        cnf.indice = None
        return


def build_indice(cnf):
    if os.path.isfile(cnf.indice):
        print("#"+str(cnf.num),"<", cnf.indice)
        cnf.indice = read_yml(cnf.indice)
        return True
    if build_indice_from_local(cnf) is False:
        build_indice_from_web(cnf)
    if cnf.indice and isinstance(cnf.indice, dict):
        return True
    return False
