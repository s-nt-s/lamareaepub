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

'''
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
    '--debug', help='Directorio para inventariar los cambios')
parser.add_argument('--fuente', help='Fichero html de fuente', required=True)
parser.add_argument(
    '--epub', help='Ebup o directorio con su contenido', required=True)
parser.add_argument('--out', help='Epub de salida', required=True)


arg = parser.parse_args()
'''

ancho_defecto = 544 # 600 - 20
ancho_anuncio = 400
ancho_autor = 144
ancho_grande = 720 # 1536 #1240
ancho_gigante = 2048 #int(ancho_grande * 2)

brillo_min = 60
brillo_max = 255 - brillo_min

MB = 1048576

refile = re.compile(r"^file\d+\.[a-z]+$")
coord=re.compile(r"^(\d+)x(\d+)\+(\d+)\+(\d+)$")

grey = ["-colorspace", "GRAY"]
trim = ["+repage", "-fuzz", "600", "-trim"]
    
tmp_wks = tempfile.mkdtemp()

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

def descargar(url):
    dwn = tmp_wks + os.path.basename(url)
    try:
        urllib.request.urlretrieve(url, dwn)
    except:
        call(["wget", url, "--quiet", "-O", dwn])
    return dwn


def optimizar_portada(arg, img):
    crop = []
    if arg.trim:
        crop1 = check_output(["convert", img] + ["+repage", "-gravity", "South", "-crop", "0%x50%+0+50%", "-fuzz", "600", "-format", "%@", "info:"])
        crop2 = check_output(["convert", img] + ["+repage", "-fuzz", "600", "-format", "%@", "info:"])
        crop1 = crop1.decode('utf-8')
        crop2 = crop2.decode('utf-8')
        a, _, c, _ = coord.findall(crop1)[0]
        '''
        c = str(int(c)-5)
        a = str(int(a)+5)
        '''
        _, b, _, d = coord.findall(crop2)[0]
        cropZ = a +'x' + b + '+' + c + '+' + d
        crop = ["+repage", "-crop", cropZ]

    cmds = ["mogrify", "-strip"] + crop
    '''
    if arg.grey:
        cmds.extend(grey)
    '''
    if arg.resize:
        cmds.extend(["-resize", str(ancho_grande) + ">"])
    return cmds

def optimizar(arg, mogrify, autores, graficas, s):
    nombre = os.path.basename(s)
    antes = os.path.getsize(s)
    im = Image.open(s)
    ancho, alto = im.size
    c = tmp_wks + os.path.basename(s)
    shutil.copy(s, c)

    portada = not refile.match(nombre)
    grafica = False

    if portada:
        cmds = optimizar_portada(arg, c)
    else:
        resize = []
        if arg.resize:
            if s in autores:
                resize = ["-resize", str(ancho_autor) + ">"]
            elif s in graficas:
                grafica = True
                resize = ["-resize", str(ancho_gigante) + ">"]
            else:
                resize = ["-resize", str(ancho_defecto) + ">"]
        cmds = mogrify + resize
        quality = int(check_output(["identify", "-format", "%Q", s]))
        if quality>75:
            cmds = cmds + ["-quality", "75"]

    if grafica:
        cmds = [c for c in cmds if c not in grey]

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

def tune_epub(arg):

    if arg.debug and not os.path.isdir(arg.debug):
        sys.exit(arg.debug + " no es un directorio")
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

    mogrify = ["mogrify", "-strip"]

    if arg.trim:
        mogrify.extend(trim)
    if arg.grey:
        mogrify.extend(grey)

    media = tmp_out + "/media/"

    autores=set()
    graficas=set()

    for xhtml in glob.glob(tmp_out+"/*.xhtml"):
        with open(xhtml, "rb") as f:
            soup = bs4.BeautifulSoup(f, "lxml")
            for i in soup.select("div.autor img"):
                autores.add(tmp_out+"/"+i.attrs["src"])
            for i in soup.select("img.grafica"):
                graficas.add(tmp_out+"/"+i.attrs["src"])
        
    imgs = []
    for g in ('*.jpeg', '*.jpg', '*.png'):
        imgs.extend(glob.glob(media + g))

    print ("Limpiando imagenes")
    antes = sum(map(os.path.getsize, imgs))
    call(["exiftool", "-r", "-overwrite_original", "-q", "-all=", media])
    despu = sum(map(os.path.getsize, imgs))
    print ("Ahorrado borrando exif: " + sizeof_fmt(antes - despu))
    imgs = sorted(imgs)
    for img in imgs:
        optimizar(arg, mogrify, autores, graficas, img)
    despu = despu - sum([os.path.getsize(s) for s in imgs])
    if despu > 0:
        print ("Ahorrado optimizando: " + sizeof_fmt(despu))

    with zipfile.ZipFile(arg.out, "w") as zip_file:
        z = len(tmp_out) + 1
        zip_file.write(tmp_out + '/mimetype', 'mimetype', compress_type=zipfile.ZIP_STORED)
        for root, dirs, files in os.walk(tmp_out):
            for f in files:
                path = os.path.join(root, f)
                name = path[z:]
                if name != 'mimetype':
                    zip_file.write(path, name, compress_type=zipfile.ZIP_DEFLATED)
    print ("Epub final de " + sizeof_fmt(os.path.getsize(arg.out)))
