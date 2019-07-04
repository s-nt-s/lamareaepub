#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse
import yaml
import sys
import os
from bunch import Bunch
from core.lamareahtml import LaMarea, tune_html_for_epub
from core.util import get_html
from core.j2 import Jnj2, my_date
from core.tratar_imgs import tune_epub
from glob import glob
import re
from subprocess import run, DEVNULL, call, check_output
import os
import tempfile
import epub_meta
import base64
import crypt
import textwrap
import bs4
import requests
from datetime import datetime
from urllib.parse import unquote
import json
from feedgen.feed import FeedGenerator
import pytz

parser = argparse.ArgumentParser(description='Genera html único y epub a partir de www.revista.lamarea.com')
parser.add_argument("--num", nargs='*', type=int, help="Números a generar (por defecto son todos)")
parser.add_argument('--refrescar', action='store_true', help="Refresca los html locales")
parser.add_argument('--html', action='store_true', help="Generar los html")
parser.add_argument('--epub', action='store_true', help="Generar los epub en base a los html")
parser.add_argument('--index', action='store_true', help="Generar el index en base a los epub")
parser.add_argument('--todo', action='store_true', help="Genera todo")
parser.add_argument('--rss', type=str, help="Genera un RSS y necesita como parámetro la url del dominio")
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
    generator = yaml.load_all(f, Loader=yaml.FullLoader)
    config = next(generator)
    for d in generator:
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
                    graficas.add(unquote(l))

    for num, d in sorted([(k, v) for k,v in config.items() if isinstance(k, int)]):
        if arg.num is None or num in arg.num:
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

if arg.index or arg.rss or arg.todo:
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
        data[num]=meta

        dt = config[int(num)]
        with open(htpasswd_dir+"lamarea_"+num+".htpasswd", "w") as f:
            f.write("%s:%s\n" % (dt['usuario'], crypt.crypt(dt['clave'], 'salt')))
            #f.write("%s:%s" % (config['usuario'], crypt.crypt(config['clave'], 'salt')))
        nginx_config = nginx_config + textwrap.dedent('''
            location ~* .+\\blamarea_%s\\..+ {
                auth_basic "Inserta el usuario y clave para el ejemplar %s de La Marea. Si no lo tienes, ve a https://kiosco.lamarea.com/";
                auth_basic_user_file /etc/nginx/htpasswd/lamarea_%s.htpasswd;
            }
        ''' % (num, num, num)).lstrip()

    with open(out_dir+"lamarea.nginx", "w") as f:
        f.write(nginx_config)

    now = datetime.now(pytz.timezone("Europe/Madrid"))

    html = j2.save(
        "index.html",
        data=data,
        now=now.strftime("%d-%m-%Y %H:%M")
    )

    html = bs4.BeautifulSoup(html, "lxml")
    info = html.find("div", attrs={"id": "info"})

    if arg.rss:
        WEB_SITE = "http://" + arg.rss
        fg = FeedGenerator()
        fg.title('La Marea en EPUB')
        fg.link(href=WEB_SITE)
        fg.description('<![CDATA['+str(info)+']]>')
        fg.pubDate(now)
        fg.language('es')

        for num, meta  in sorted(data.items()):
            epub_url = WEB_SITE+("/epub/lamarea_%s.epub" % num)

            fe = fg.add_entry()
            fe.title(meta['title'][9:])
            fe.link(href=epub_url)
            fe.pubDate(meta['publication_date'])
            fe.enclosure(url=epub_url, length=str(meta['file_size_in_bytes']), type='application/epub+zip')
            fe.guid(guid=epub_url, permalink=True)
            fe.description("Número de "+my_date(meta['publication_date'], True).lower())

        fg.rss_file(out_dir+'rss.xml')
