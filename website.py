#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse
import yaml
import sys
import os
from bunch import Bunch
from core.lamareahtml import LaMarea, tune_html_for_epub
from core.util import get_html, get_config, make_autocontenido
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
from subprocess import DEVNULL
import shlex
from shutil import copy, move

parser = argparse.ArgumentParser(description='Genera una web para listar los epubs')
parser.add_argument("config", nargs='?', help="Fichero de configuración en formato Yaml", default="lamarea.yml")

arg = parser.parse_args()

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

config = get_config(arg.config)

j2 = Jnj2("j2/", config.out_dir)
cnfnum = sorted([(k, v) for k,v in config.items() if isinstance(k, int)])

for num, cnf in cnfnum:
    meta = epub_meta.get_epub_metadata(cnf.epub)
    img_path = config.cover_dir+str(num)+meta['cover_image_extension']
    with open(img_path, "wb") as fh:
        fh.write(base64.decodebytes(meta['cover_image_content']))
    call(["mogrify", "-strip", "-resize", "x275", "-quality", "75", img_path])
    del meta['cover_image_content']
    cnf.meta=meta
    if not os.path.isfile(cnf.zip):
        copy(cnf.html, cnf.html+".bak")
        make_autocontenido(cnf.html)
        call(['zip', '-j', '-9', '-P', cnf.clave, cnf.zip, cnf.epub, cnf.html], stdout=DEVNULL)
        move(cnf.html+".bak", cnf.html)

now = datetime.now(pytz.timezone("Europe/Madrid"))

html = j2.save(
    "index.html",
    data=cnfnum,
    out_dir=config.out_dir,
    now=now.strftime("%d-%m-%Y %H:%M")
)

html = bs4.BeautifulSoup(html, "lxml")
info = html.find("div", attrs={"id": "info"})

fg = FeedGenerator()
fg.title('La Marea en EPUB')
fg.link(href=config.website)
fg.description('<![CDATA['+str(info)+']]>')
fg.pubDate(now)
fg.language('es')

for num, cnf in cnfnum:
    zip_url = config.website+("/zip/lamarea_%s.zip" % num)

    fe = fg.add_entry()
    fe.title(cnf.meta['title'][9:])
    fe.link(href=zip_url)
    fe.pubDate(cnf.meta['publication_date'])
    fe.enclosure(url=zip_url, length=str(cnf.meta['file_size_in_bytes']), type='application/zip')
    fe.guid(guid=zip_url, permalink=True)
    fe.description("Número de "+my_date(cnf.meta['publication_date'], True).lower())

fg.rss_file(config.out_dir+'rss.xml')
