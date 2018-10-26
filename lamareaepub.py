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
import crypt
import textwrap
import bs4
import requests

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
htpasswd_dir = out_dir+"htpasswd/"

if not os.path.isfile(arg.config):
    sys.exit(arg.config+" no existe")

def get_path_html(num):
    return html_dir + "lamarea_" + str(num) + ".html"


with open(arg.config, 'r') as f:
    config={}
    for d in yaml.load_all(f):
        if "url" not in d:
            d["url"] = "http://www.revista.lamarea.com/"
        if "usuario" not in d:
            d["usuario"] = "LM"+str(d["num"])

        for k in ("portada", "fecha", "titulo"):
            if k not in d:
                d[k] = None
        config[d['num']] = d

if arg.html or arg.todo:
    graficas = set()
    if os.path.isfile("graficas.txt"):
        with open("graficas.txt", 'r') as f:
            for l in f.readlines():
                l = l.strip()
                if len(l)>0 and not l.startswith("#"):
                    graficas.add(l)

    for num, d in sorted(config.items()):
        if arg.num is None or numm in arg.num:
            if num == 62:
                continue
            html_path  = get_path_html(num)

            if not arg.refrescar and os.path.isfile(html_path):
                continue

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

def get_html_bytes(num):
    return ">10 MB"
    html_file = get_path_html(num)
    size = os.path.getsize(html_file)
    with open(html_file, "r") as f:
        contents = f.read()
        soup = bs4.BeautifulSoup(contents, "lxml")
        for img in soup.select("img[src]"):
            url = img.attrs["src"]
            if url.startswith("http"):
                d = requests.head(url)
                s = d.headers.get('Content-Length', 0)
                size = size + int(s)
    return size

if arg.index or arg.todo:
    data = {}
    j2 = Jnj2("j2/", out_dir)
    nginx_config = ""
    for epub_file in sorted(glob(epub_dir+"*.epub")):
        num = re.sub(r"\D", "", epub_file)
        meta = epub_meta.get_epub_metadata(epub_file)
        img_path = cover_dir+num+meta['cover_image_extension']
        with open(img_path, "wb") as fh:
            fh.write(base64.decodebytes(meta['cover_image_content']))
        call(["mogrify", "-strip", "-resize", "x275", "-quality", "75", img_path])
        del meta['cover_image_content']
        meta['html_size_in_bytes'] = get_html_bytes(num)
        data[num]=meta

        dt = config[int(num)]
        with open(htpasswd_dir+"lamarea_"+num+".htpasswd", "w") as f:
            f.write("%s:%s" % (dt['usuario'], crypt.crypt(dt['clave'], 'salt')))
        nginx_config = nginx_config + textwrap.dedent('''
            location ~* .+\\blamarea_%s\\..+ {
                auth_basic "Inserta el usuario y clave para el ejemplar %s de La Marea";
                auth_basic_user_file /etc/nginx/htpasswd/lamarea_%s.htpasswd;
            }
        ''' % (num, num, num)).lstrip()

    with open(out_dir+"lamarea.nginx", "w") as f:
        f.write(nginx_config)

    j2.save(
        "index.html",
        data=data
    )

