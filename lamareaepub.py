#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse
import yaml
import sys
import os
from bunch import Bunch
from core.lamareahtml import LaMarea, tune_html_for_epub
from core.util import get_html
from core.j2 import Jnj2
from core.tratar_imgs import tune_epub
from glob import glob
import re
from subprocess import run, DEVNULL, call
import os
import tempfile
import epub_meta
import base64

parser = argparse.ArgumentParser(description='Genera html único y epub a partir de www.revista.lamarea.com')
parser.add_argument("--num", nargs='*', type=int, help="Números a generar (por defecto son todos)")
parser.add_argument('--refrescar', action='store_true', help="Refresca los html locales")
parser.add_argument('--html', action='store_true', help="Generar los html")
parser.add_argument('--epub', action='store_true', help="Generar los epub en base a los html")
parser.add_argument('--index', action='store_true', help="Generar el index en base a los epub")
parser.add_argument('--todo', action='store_true', help="Genera todo")
parser.add_argument("config", nargs='?', help="Fichero de configuración en formato Yaml", default="lamarea.yml")

arg = parser.parse_args()

out_dir = "out/"
html_dir = out_dir+ "html/"
epub_dir = out_dir +"epub/"
cover_dir = out_dir+ "portada/"

if not os.path.isfile(arg.config):
    sys.exit(arg.config+" no existe")

def get_path_html(num):
    return html_dir + "lamarea_" + str(num) + ".html"

if arg.html or arg.todo:
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

if arg.epub or arg.todo:
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

            #print(html_tune)
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

if arg.index or arg.todo:
    data = {}
    j2 = Jnj2("j2/", out_dir)
    for epub_file in sorted(glob(epub_dir+"*.epub")):
        num = re.sub(r"\D", "", epub_file)
        meta = epub_meta.get_epub_metadata(epub_file)
        img_path = cover_dir+num+meta['cover_image_extension']
        with open(img_path, "wb") as fh:
            fh.write(base64.decodebytes(meta['cover_image_content']))
        call(["mogrify", "-strip", "-resize", "x275", "-quality", "75", img_path])
        del meta['cover_image_content']
        data[num]=meta

    j2.save(
        "index.html",
        data=data
    )

