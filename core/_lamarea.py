# -*- coding: utf-8 -*-

import sys
from mechanize import Browser
import bs4
import re
import argparse
import time
from urlparse import urljoin
from urlparse import urlparse
from os.path import splitext

parser = argparse.ArgumentParser(
    description='Genera un html único a partir de www.revista.lamarea.com')
parser.add_argument("url", help="Url completa al número de la revista")
parser.add_argument(
    '--usuario', help='Usuario de acceso a www.revista.lamarea.com', required=True)
parser.add_argument(
    '--clave', help='Contraseña de acceso www.revista.lamarea.com', required=True)
parser.add_argument(
    '--apendices', help='Genera un capítulo de apendices con los conetenidos de los enlaces a www.lamarea.com', required=False, action="store_true")
parser.add_argument(
    '--recursivo', help='Esta opción combinada con --apendices busca apendices de manera recursiva', required=False, action="store_true")
parser.add_argument(
    '--num', type=int, help='Número de la edicción')
parser.add_argument(
    '--portada', help='URL a la portada del número')
parser.add_argument(
    '--fecha', help='Fecha de publicación')

arg = parser.parse_args()

rPortada = re.compile(r'"body_bg"\s*:\s*"\s*([^"]+)\s*"', re.IGNORECASE)
tab = re.compile("^", re.MULTILINE)
nonumb = re.compile("\D+")
re_apendices = re.compile(r"^https?://www.lamarea.com/2\d+/\d+/\d+/.*")
re_scribd = re.compile(r"^(https://www.scribd.com/embeds/\d+)/.*")
re_youtube = re.compile(r"https://www.youtube.com/embed/(.+?)\?.*")

tag_concat = ['u', 'ul', 'ol', 'i', 'em', 'strong', 'b']
tag_round = ['u', 'i', 'em', 'span', 'strong', 'a', 'b']
tag_trim = ['li', 'th', 'td', 'div', 'caption', 'h[1-6]']
tag_right = ['p']
sp = re.compile("\s+", re.UNICODE)
nb = re.compile("^\s*\d+\.\s+", re.UNICODE)

heads = ["h1", "h2", "h3", "h4", "h5", "h6"]
block = heads + ["p", "div", "table", "article"]
inline = ["span", "strong", "b", "del", "i", "em"]

urls = ["#", "javascript:void(0)"]
editorial = None

meses = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

br = Browser()


def get_html(soup):
    h = unicode(soup)
    r = re.compile("(\s*\.\s*)</a>", re.MULTILINE | re.DOTALL | re.UNICODE)
    h = r.sub("</a>\\1", h)
    for t in tag_concat:
        r = re.compile(
            "</" + t + ">(\s*)<" + t + ">", re.MULTILINE | re.DOTALL | re.UNICODE)
        h = r.sub("\\1", h)
    for t in tag_round:
        r = re.compile(
            "(<" + t + ">)(\s+)", re.MULTILINE | re.DOTALL | re.UNICODE)
        h = r.sub("\\2\\1", h)
        r = re.compile(
            "(<" + t + " [^>]+>)(\s+)", re.MULTILINE | re.DOTALL | re.UNICODE)
        h = r.sub("\\2\\1", h)
        r = re.compile(
            "(\s+)(</" + t + ">)", re.MULTILINE | re.DOTALL | re.UNICODE)
        h = r.sub("\\2\\1", h)
    for t in tag_trim:
        r = re.compile(
            "(<" + t + ">)\s+", re.MULTILINE | re.DOTALL | re.UNICODE)
        h = r.sub("\\1", h)
        r = re.compile(
            "\s+(</" + t + ">)", re.MULTILINE | re.DOTALL | re.UNICODE)
        h = r.sub("\\1", h)
    for t in tag_right:
        r = re.compile(
            "\s+(</" + t + ">)", re.MULTILINE | re.DOTALL | re.UNICODE)
        h = r.sub("\\1", h)
        r = re.compile(
            "(<" + t + ">) +", re.MULTILINE | re.DOTALL | re.UNICODE)
        h = r.sub("\\1", h)
    r = re.compile(
        r"\s*(<meta[^>]+>)\s*", re.MULTILINE | re.DOTALL | re.UNICODE)
    h = r.sub(r"\n\1\n", h)
    r = re.compile(r"\n\n+", re.MULTILINE | re.DOTALL | re.UNICODE)
    h = r.sub(r"\n", h)
    return h


def get_tpt(title, img):
    soup = bs4.BeautifulSoup('''
	<!DOCTYPE html>
	<html lang="es">
		<head>
			<title>%s</title>
			<meta charset="utf-8"/>
            <link rel="stylesheet" type="text/css" href="theme.css">
            <link rel="stylesheet" type="text/css" href="print.css" media="print">
			<meta property="og:image" content="%s" />
			<meta content="La Marea" name="DC.creator" />
			<meta content="MásPúblico" name="DC.publisher" />
			<meta content="Creative Commons BY/SA 3.0" name="DC.rights" />
		</head>
		<body>
		</body>
	</html>
	''' % (title, img)
        , 'lxml')
    return soup



def get_title(url):
    is_scribd = re_scribd.match(url)
    if is_scribd:
        url = url.replace("/embeds/","/doc/")
    try:
        html = br.open(url).read()
        a=html.find('<title>')
        if a>0:
            a += 7
            b=html.find('</title>', a)
            title=sp.sub(" ",html[a:b]).strip()
            return title
    except:
        pass
    if is_scribd:
        url = is_scribd.group(1)
        url = url.replace("/embeds/","/doc/")
    return url


def limpiar(nodo):
    for s in nodo.findAll("span"):
        if "style" not in s.attrs:
            s.unwrap()

    for i in nodo.findAll("iframe"):
        src = i.attrs["src"]
        busca_href = src
        is_scribd = re_scribd.match(src)
        is_youtube = re_youtube.match(src)
        if is_scribd:
            busca_href = is_scribd.group(1)
            busca_href = busca_href.replace("/embeds/","/(doc|embeds)/")
            busca_href = re.compile("^"+busca_href+"(/.*)?$")
            src = src.replace("/embeds/","/doc/")
        elif is_youtube:
            busca_href = is_youtube.group(1)
            src = "https://www.youtube.com/watch?v=" + busca_href
            busca_href = re.compile("^https?://www.youtube.com/.*\b"+busca_href+"\b.*$")
        if nodo.findAll("a", attrs={'href': busca_href}):
            i.extract()
        else:
            i.name="a"
            i.attrs.clear()
            i.attrs["href"] = src
            i.attrs["target"] = "_blank"
            i.string=get_title(src)

    for i in nodo.findAll(block):
        if i.find("img"):
            continue
        txt = sp.sub("", i.get_text().strip())
        if len(txt) == 0 or txt == "." or txt == "FALTAIMAGENPORTADA":
            i.extract()
        else:
            i2 = i.select(" > " + i.name)
            if len(i2) == 1:
                txt2 = sp.sub("", i2[0].get_text().strip())
                if txt == txt2:
                    i.unwrap()

    for i in nodo.findAll(inline):
        txt = sp.sub("", i.get_text().strip())
        if len(txt) == 0:
            i.unwrap()

    for i in nodo.findAll(block + inline):
        i2 = i.select(" > " + i.name)
        if len(i2) == 1:
            txt = sp.sub("", i.get_text()).strip()
            txt2 = sp.sub("", i2[0].get_text()).strip()
            if txt == txt2:
                i.unwrap()

    for h in nodo.findAll(heads):
        txt = sp.sub(" ", h.get_text().strip())
        if len(txt.split(" "))>50:
            h.name="p"

    for t in nodo.findAll("table"):
        flag = True
        for td in t.findAll(["td", "th"]):
            txt = sp.sub(" ",td.get_text()).strip()
            for p in td.select("> p"):
                p_txt = sp.sub(" ",p.get_text()).strip()
                if p_txt != txt:
                    flag = False
        if flag:
            for p in t.select("td > p") + t.select("th > p"):
                p.unwrap()
        flag = True
        m_tds = -1
        for tr in t.findAll("tr"):
            tds = tr.findAll(["td", "th"])
            m_tds = max(m_tds, len(tds))
            for td in tds:
                if td.attrs.get("colspan", None):
                    flag = False
        if flag:
            for i in range(m_tds-1, -1, -1):
                flag = True
                col = []
                for tr in t.findAll("tr"):
                    tds = tr.findAll(["td", "th"])
                    if len(tds)>i:
                        td = tds[i]
                        col.append(td)
                        txt = len(sp.sub("",td.get_text()))
                        if txt > 0 or len(td.findAll("img"))>0:
                            flag = False
                if flag:
                    m_tds = m_tds -1
                    for td in col:
                        td.extract()
            if m_tds > 1:
                for tr in t.findAll("tr"):
                    tds = tr.findAll(["td", "th"])
                    if len(tds)==1:
                        tds[0].attrs["colspan"] = m_tds

def limpiar2(nodo, url=None):
    for img in nodo.select("a > img"):
        a = img.parent
        if len(a.get_text().strip()) == 0:
            href = a.attrs["href"]
            src = img.attrs["src"]
            if url:
                hrf = urljoin(url, href)
                src = urljoin(url, src)
                if urlparse(hrf).netloc != urlparse(src).netloc:
                    continue
            _, ext1 = splitext(urlparse(href).path)
            _, ext2 = splitext(urlparse(src).path)
            if ext1 in (".pdf",):
                srcset = img.attrs.get("srcset", "").split(", ")[-1].split(" ")[0].strip()
                if len(srcset)>0:
                    img.attrs["src"] = srcset
                continue
            img.attrs["src"] = href
            a.unwrap()
    for n in nodo.findAll(heads + ["p", "div", "span", "strong", "b", "i", "article"]):
        style = None
        id = None
        if "style" in n.attrs:
            style = n.attrs["style"]
        if "id" in n.attrs:
            id = n.attrs["id"]
        elif n.name == "span":
            n.unwrap()
            continue
        n.attrs.clear()
        if style:
            n.attrs["style"] = style
        if id and n.name in heads and id.startswith("http"):
            n.attrs["id"] = id

def rutas(url, soup):
    for a in soup.findAll(["a", "img", "iframe"]):
        attr = "href" if a.name == "a" else "src"
        href = a.attrs.get(attr, None)
        if not href:
            continue
        if href.startswith("www."):
            href = "http://" + href
        else:
            href = urljoin(url, href)
        a.attrs[attr] = href


page = br.open(arg.url)

if not arg.portada:
    m = rPortada.search(page.read())
    if m:
        arg.portada = m.group(1).replace("\\/", "/")


br.select_form(name="login-form")
br.form["log"] = arg.usuario
br.form["pwd"] = arg.clave
page = br.submit()

soup = bs4.BeautifulSoup(page.read(), "lxml")



print unicode(lamarea)




