#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse
import yaml
import sys
import os
from bunch import Bunch
from core.lamareahtml import LaMarea, tune_html_for_epub
from core.util import get_html
from core.tratar_imgs import tune_epub
from glob import glob
import re
from subprocess import run, DEVNULL
import os
import tempfile

parser = argparse.ArgumentParser(description='Genera html único y epub a partir de www.revista.lamarea.com')
parser.add_argument("--num", nargs='*', type=int, help="Números a generar (por defecto son todos)")
parser.add_argument('--refrescar', action='store_true', help="Refresca los html locales")
parser.add_argument('--solo-html', action='store_true', help="Generar solo los html")
parser.add_argument("config", nargs='?', help="Fichero de configuración en formato Yaml", default="lamarea.yml")

arg = parser.parse_args()

html_dir = "out/html/"
epub_dir = "out/epub/"

if not os.path.isfile(arg.config):
    sys.exit(arg.config+" no existe")

def get_path_html(num):
    return html_dir + "lamarea_" + str(num) + ".html"

graficas = set()
if os.path.isfile("graficas.txt"):
    with open("graficas.txt", 'r') as f:
        for l in f.readlines():
            l = l.strip()
            if len(l)>0 and not l.startswith("#"):
                graficas.add(l)

with open(arg.config, 'r') as f:
    for d in yaml.load_all(f):
        if arg.num is None or d['num'] in arg.num:
            html_path  = get_path_html(d['num'])

            if not arg.refrescar and os.path.isfile(html_path):
                continue
            
            if "url" not in d:
                d["url"] = "http://www.revista.lamarea.com/"
            if "usuario" not in d:
                d["usuario"] = "LM"+str(d["num"])

            for k in ("portada", "fecha", "titulo"):
                if k not in d:
                    d[k] = None

            d["graficas"] = graficas

            m = LaMarea(Bunch(d))
            h = get_html(m.soup)
            with open(html_path, "w") as file:
                file.write(h)

            print ("")

for html_file in glob(html_dir+"*.tmp.html"):
    os.remove(html_file)

if arg.solo_html:
    sys.exit()

for html_file in sorted(glob(html_dir+"*.html")):
    num = int(re.sub(r"\D", "", html_file))
    if arg.num is None or num in arg.num:
        print ("")
        print("====== La Marea #"+str(num)+" ======")

        '''
        epub = epub_dir+"HD/lamarea_"+str(num)+".epub"

        html_tune = tune_html_for_epub(html_file)
        run(["miepub", "--chapter-level", "2", "--out", epub, html_tune])
        '''
        
        html_tune = tune_html_for_epub(html_file, "anuncios")

        epub = tempfile.NamedTemporaryFile(suffix='.epub', delete=True).name
        run(["miepub", "--chapter-level", "2", "--out", epub, html_tune]) #, stdout=DEVNULL)

        os.remove(html_tune)
        
        print("")
        tune_epub(Bunch(
            epub=epub,
            out=epub_dir+"lamarea_"+str(num)+".epub",
            trim=True,
            grey=True,
            resize=True,
            debug=None
        ))

