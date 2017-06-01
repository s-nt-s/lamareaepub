#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import glob
import sys
import shutil
from subprocess import call, check_output
from PIL import Image
import sys
import re
import bs4
import urllib.request
import filecmp
import zipfile
import tempfile
import argparse

parser = argparse.ArgumentParser(
    description='Trata las imagenes para ahorrar espacio')
parser.add_argument(
    '--grey', help='Pasar las imagenes a blanco y negro', action="store_true")
parser.add_argument(
    '--trim', help='Recortar las imagenes para eliminar margenes', action="store_true")
parser.add_argument(
    '--resize', help='Redimensionar las imagenes', action="store_true")
parser.add_argument(
    '--debug', help='Directorio para ver inventariar los cambios')
parser.add_argument('--fuente', help='Fichero html de fuente', required=True)
parser.add_argument(
    '--epub', help='Ebup o directorio con su contenido', required=True)
parser.add_argument('--out', help='Epub de salida', required=True)


arg = parser.parse_args()

if arg.debug and not os.path.isdir(arg.debug):
    sys.exit(arg.debug + " no es un directorio")
if not arg.fuente.endswith(".html") or not os.path.isfile(arg.fuente):
    sys.exit(arg.fuente + " no es un fichero html")
if os.path.isfile(arg.epub):
    if not arg.epub.endswith(".epub"):
        sys.exit(arg.epub + " no es un epub")
    else:
        tmp_out = tempfile.mkdtemp()
        with zipfile.ZipFile(arg.epub, 'r') as zip_ref:
            zip_ref.extractall(tmp_out)
            zip_ref.close()
elif not os.path.isdir(arg.epub):
    sys.exit(arg.epub + " no es un directorio ni un fichero epub")
else:
    tmp_out = arg.epub

ancho_defecto = 544 # 600 - 20
ancho_anuncio = 400
ancho_autor = 144
ancho_grande = 720 # 1536 #1240
ancho_gigante = 2048 #int(ancho_grande * 2)

brillo_min = 60
brillo_max = 255 - brillo_min

mogrify = ["mogrify"]
grey = ["-colorspace", "GRAY"]
trim = ["-strip", "+repage", "-fuzz", "600", "-trim"]

MB = 1048576

if arg.trim:
    mogrify.extend(trim)
if arg.grey:
    mogrify.extend(grey)

refile = re.compile(r"^file\d+\.[a-z]+$")

tmp_wks = tempfile.mkdtemp()
media = tmp_out + "/media/"


def descargar(url):
    dwn = tmp_wks + os.path.basename(url)
    try:
        urllib.request.urlretrieve(url, dwn)
    except:
        call(["wget", url, "--quiet", "-O", dwn])
    return dwn


def sizeof_fmt(num, suffix='B'):
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f %s%s" % (num, 'Y', suffix)


def igual(arr, f):
    for a in arr:
        if filecmp.cmp(a, f):
            return a
    return None

with open(arg.fuente, "rb") as f:
    soup = bs4.BeautifulSoup(f, "lxml")
    autores = [a.attrs["src"] for a in soup.select("div.autor img")]
    ab = soup.find("h2", text=re.compile(
        r"^\s*(anuncios\s+breves|publicidad\s+.tica)\s*$", re.UNICODE | re.MULTILINE | re.IGNORECASE))
    ar = ab.find_next_sibling("article") if ab else None
    anuncios = [a.attrs["src"] for a in ar.select("img")] if ar else []

autores = list(map(descargar, autores))
anuncios = list(map(descargar, anuncios))


def composicion(im):
    ancho, alto = im.size
    pc = 0
    bl = 0
    ng = 0
    cl = 0
    tt = 0
    for c in im.convert('RGB').getcolors(ancho * alto):
        cnt = c[0]
        rgb = c[1]
        brillo = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
        if brillo > brillo_max:  # blanco
            bl += cnt
        elif brillo < brillo_min:  # negro
            ng += cnt
            cl += cnt
        tt += cnt
    return int(bl * 100 / tt), int(ng * 100 / tt), int(cl * 100 / tt), tt

imgs = []
for g in ['*.jpeg', '*.jpg', '*.png']:
    imgs.extend(glob.glob(media + g))

for i in range(len(autores)):
    a = igual(imgs, autores[i])
    autores[i] = a if a else None
for i in range(len(anuncios)):
    a = igual(imgs, anuncios[i])
    anuncios[i] = a if a else None


def optimizar(s):
    nombre = os.path.basename(s)
    antes = os.path.getsize(s)
    im = Image.open(s)
    ancho, alto = im.size
    c = tmp_wks + os.path.basename(s)
    shutil.copy(s, c)

    portada = not refile.match(nombre)

    resize = []
    if arg.resize:
        if portada:
            resize = ["-resize", str(ancho_grande) + ">"]
        elif s in anuncios:
            resize = ["-resize", str(ancho_anuncio) + ">"]
        elif s in autores:
            resize = ["-resize", str(ancho_autor) + ">"]
        else:
            blanco, negro, color, total = composicion(im)
            if ((blanco + negro) > 80 and blanco > 70): # grafica
                resize = ["-resize", str(ancho_gigante) + ">"]
                '''
                if antes > MB:
                    resize = ["-resize", str(ancho_gigante) + ">"]
                    if s.endswith(".jpg") or s.endswith(".jpeg"):
                        resize.extend(["-quality", "60"])
                        #resize.extend(["-define", "jpeg:extent=1024KB"])
                '''
            else:
                resize = ["-resize", str(ancho_defecto) + ">"]

    cmds = mogrify + resize

    if arg.grey and portada:
        cmds = [x for x in cmds if x not in grey]

    call(cmds + [c])

    despues = os.path.getsize(c)

    if arg.debug:
        nombre = os.path.basename(s)
        nombre, extension = os.path.splitext(nombre)
        nombre = arg.debug + arg.epub[8:10] + "_" + nombre

        shutil.copy(s, nombre + "_" + extension)
        shutil.copy(c, nombre + "_" + "_".join(cmds[1:-1]).replace(">","") + extension)

    if antes > despues:
        shutil.move(c, s)
    elif arg.trim:
        ancho2, alto2 = Image.open(c).size
        if (ancho - ancho2) > 20 or (alto - alto2) > 20:
            shutil.move(c, s)

print ("Limpiando imagenes")
antes = sum(map(os.path.getsize, imgs))
call(["exiftool", "-r", "-overwrite_original", "-q", "-all=", media])
despu = sum(map(os.path.getsize, imgs))
print ("Ahorrado borrando exif: " + sizeof_fmt(antes - despu))
imgs = sorted(imgs)
for img in imgs:
    optimizar(img)
despu = despu - sum([os.path.getsize(s) for s in imgs])
if despu > 0:
    print ("Ahorrado optimizando: " + sizeof_fmt(despu))

if arg.out:
    with zipfile.ZipFile(arg.out, "w", zipfile.ZIP_DEFLATED) as zip_file:
        z = len(tmp_out) + 1
        for root, dirs, files in os.walk(tmp_out):
            for f in files:
                path = os.path.join(root, f)
                zip_file.write(path, path[z:])
