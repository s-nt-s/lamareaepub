#!/usr/bin/env python3
import argparse
from core.util import read_config
from py7zr import SevenZipFile
from os.path import basename

parser = argparse.ArgumentParser(description='Crea versiones 7z de los epub')
parser.add_argument("config", nargs='?', help="Fichero de configuración en formato Yaml", default="lamarea.yml")

arg = parser.parse_args()

config = read_config(arg.config)

out_dir = "out/"
html_dir = out_dir+ "html/"
epub_dir = out_dir +"epub/"
zip_dir = out_dir +"zip/"

for num, d in sorted([(k, v) for k,v in config.items() if isinstance(k, int)]):
    z = zip_dir+"lamarea_"+str(num)+".7z"
    h = html_dir+"lamarea_"+str(num)+".html"
    e = epub_dir+"lamarea_"+str(num)+".epub"
    print(z)
    with SevenZipFile(z, 'w', password=d['clave']) as arc:
        for f in (h, e):
            arc.write(f, basename(f))
