# -*- coding: utf-8 -*-

import sys
from mechanize import Browser
import bs4
import re
import argparse
import time

parser = argparse.ArgumentParser(
    description='Genera un html único a partir de www.revista.lamarea.com')
parser.add_argument("url", help="Url completa al número de la revista")
parser.add_argument(
    '--usuario', help='Usuario de acceso a www.revista.lamarea.com', required=True)
parser.add_argument(
    '--clave', help='Contraseña de acceso www.revista.lamarea.com', required=True)
parser.add_argument(
    '--apendices', help='Genera un capítulo de apendices con los conetenidos de los enlaces a www.lamarea.com', required=False, action="store_true")

arg = parser.parse_args()

rPortada = re.compile(
    r"http://www.revista.lamarea.com/\S*?\bwp-content/uploads/\S*?/\S*?Portada\S*?.jpg", re.IGNORECASE)
tab = re.compile("^", re.MULTILINE)
sp = re.compile("\s+", re.UNICODE)
nonumb = re.compile("\D+")

tag_concat = ['u', 'ul', 'ol', 'i', 'em', 'strong']
tag_round = ['u', 'i', 'em', 'span', 'strong', 'a']
tag_trim = ['li', 'th', 'td', 'div', 'caption', 'h[1-6]']
tag_right = ['p']
sp = re.compile("\s+", re.UNICODE)
nb = re.compile("^\s*\d+\.\s+", re.UNICODE)

heads = ["h1", "h2", "h3", "h4", "h5", "h6"]
block = heads + ["p", "div", "table", "article"]
inline = ["span", "strong", "b"]

urls = ["#", "javascript:void(0)"]
editorial = None

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
			<link href="main.css" rel="stylesheet" type="text/css"/>
			<meta content="La Marea" name="DC.creator" />
			<meta content="MásPúblico" name="DC.publisher" />
			<meta content="Creative Commons BY/SA 3.0" name="DC.rights" />
			<meta property="og:image" content="%s" />
		</head>
		<body>
		</body>
	</html>
	''' % (title, img)
        , 'lxml')
    return soup


def get_enlaces(soup, hjs=[]):
    wpb = soup.find("div", attrs={'class': "wpb_wrapper"})
    if not wpb:
        return hjs
    noes = wpb.select("div.eltd-post-info-date a")
    hrefs = wpb.select(" a, ".join(heads)) + wpb.select("a")
    for h in hrefs:
        if h in noes:
            continue
        href = h.attrs["href"]
        txth = h.get_text().strip()
        if len(txth) > 0 and href not in urls and href not in hjs:
            hjs.append(h)
    return hjs


def limpiar(nodo):
    for s in nodo.findAll("span"):
        if "style" not in s.attrs:
            s.unwrap()

    for i in nodo.findAll(block):
        if i.find("img"):
            continue
        txt = sp.sub("", i.get_text().strip())
        if len(txt) == 0 or txt == ".":
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


def limpiar2(nodo):
    for img in nodo.select("a > img"):
        a = img.parent
        if len(a.get_text().strip()) == 0:
            img.attrs["src"] = a.attrs["href"]
            a.unwrap()
    for n in nodo.findAll(heads + ["p", "div", "span", "strong", "b", "i", "article"]):
        style = None
        if "style" in n.attrs:
            style = n.attrs["style"]
        elif n.name == "span":
            n.unwrap()
            continue
        n.attrs.clear()
        if style:
            n.attrs["style"] = style


class Pagina:

    def __init__(self, titulo, url, tipo=None):
        self.titulo = titulo
        self.url = url
        self.tipo = tipo
        self.hijas = []
        self.articulo = None
        self.autor = None
        if url == editorial:
            self.tipo = 999
            if titulo.lower() != "editorial":
                self.titulo = "Editorial: " + titulo
        urls.append(url)

    def add(self, a, tipo=None, hjs=[]):
        url = a.attrs["href"].strip()
        txt = a.get_text().strip()
        if len(txt) == 0 or len(url) == 0 or url in urls:
            return
        soup = None
        art = None
        if not tipo:
            page = br.open(url)
            soup = bs4.BeautifulSoup(page.read(), "lxml")
            art = soup.find("article")
            if not art:
                hjs = get_enlaces(soup, hjs)
                if len(hjs) == 0:
                    return
        p = Pagina(txt, url, tipo)
        p.articulo = art
        if p.tipo == 999:
            lamarea.hijas.insert(0, p)
            if soup and p.titulo.lower() == "editorial":
                p.titulo = "Editorial: " + soup.find("h1").get_text()
        else:
            self.hijas.append(p)
        for a in hjs:
            p.add(a)

    def __unicode__(self):
        ln = self.titulo
        ln = ln + "\n" + self.url
        st = ""
        self.reordenar_hijas()
        for h in self.hijas:
            st = st + "\n" + unicode(h)
        st = tab.sub("  ", st)
        return ln + st

    def reordenar_hijas(self):
        for i in range(len(self.hijas)-1):
            if self.hijas[i].titulo.lower() == "anuncios breves":
                self.hijas.append(self.hijas.pop(i))
                return

    def soup(self, soup=None, nivel=1):
        if self.articulo:
            if self.tipo == 999:
                if len(self.articulo.select("div.eltd-post-image img")) > 0:
                    self.articulo.find("img").extract()
                    self.articulo.find("img").extract()
            self.articulo.attrs["nivel"] = str(nivel)
            return self.articulo
        if self.tipo == 0:
            soup = get_tpt(self.titulo, self.url)

        div = soup.new_tag("div")
        for i in self.hijas:
            h = soup.new_tag("h" + str(nivel))
            h.string = i.titulo
            div.append(h)
            div.append(i.soup(soup, nivel + 1))

        if self.tipo == 0:
            soup.body.append(div)
            div.unwrap()
            return soup
        return div

page = br.open(arg.url)

portada = rPortada.search(page.read()).group()
imagenportada = portada.split('/')[-1].split('.')[0]

numero = int(nonumb.sub("", imagenportada))

lamarea = Pagina("La Marea #" + str(numero), portada, 0)

br.select_form(name="login-form")
br.form["log"] = arg.usuario
br.form["pwd"] = arg.clave
page = br.submit()

soup = bs4.BeautifulSoup(page.read(), "lxml")
editorial = soup.find("a", text="Editorial")
if editorial:
    editorial = editorial.attrs["href"]
dossier = soup.find("h2", text=re.compile(
    r"^\s*DOSSIER\s*.+", re.MULTILINE | re.DOTALL | re.UNICODE))
if dossier:
    dossier = sp.sub(" ", dossier.get_text()).strip()

for li in soup.select("#menu-header > li"):
    i = li.find("a")
    if (dossier and sp.sub(" ", i.get_text()).strip().upper() == "DOSSIER"):
        i.string = dossier
    hijas = []
    for a in li.select("ul li a"):
        hijas.append(a)
    lamarea.add(i, None, hijas)

for a in get_enlaces(soup):
    lamarea.add(a)

print unicode(lamarea)

soup = lamarea.soup()

for div in soup.select("div.eltd-post-image-area"):
    div.extract()

for i in soup.findAll(["b"]):
    i.unwrap()

limpiar(soup)

autores = []
autores_nombres = []

for art in soup.select("article"):
    art.find("div").unwrap()
    cabs = []
    nivel = int(art.attrs["nivel"])
    for n in range(1, 7):
        cab = art.select("h" + str(n))
        if len(cab) > 0:
            cabs.append(cab)
    for cab in cabs:
        for h in cab:
            h.name = "h" + str(nivel)
        nivel = nivel + 1

    for img in art.findAll("img", attrs={'src': re.compile(r".*la-marea-250x250\.jpg.*")}):
        img.extract()
    auth = art.find("div", attrs={'class': "saboxplugin-wrap"})
    if not auth:
        auth = art.find("div", attrs={'class': "saboxplugin-authorname"})
    if auth:
        aut = sp.sub(" ", auth.get_text().strip())
        if aut == "La Marea":
            auth.extract()
        else:
            autores.append(auth)
            for a in auth.select("a"):
                a.name = "strong"
                a.attrs.clear()
                aut = sp.sub(" ", a.get_text().strip())
                if len(aut) > 0 and aut == aut.upper():
                    aut = aut.title()
                    a.string = aut
            for b in auth.select("br"):
                b.extract()

limpiar2(soup)

for auth in autores:
    if auth.find("img"):
        auth.attrs["class"] = "autor conimg".split()
    else:
        auth.attrs["class"] = "autor sinimg".split()

autores_nombres = sorted(
    list(set([s.get_text() for s in soup.body.select("div.autor strong")])))
for a in autores_nombres:
    meta = soup.new_tag("meta")
    meta.attrs["name"] = "DC.contributor"
    meta.attrs["content"] = a
    soup.head.append(meta)

art1 = soup.find("article")
meta = soup.new_tag("meta")
meta.attrs["name"] = "DC.description"
meta.attrs["content"] = sp.sub(" ", art1.get_text()).strip()
soup.head.append(meta)

if arg.apendices:
    count = 1
    apendices = soup.new_tag("div")
    urls = [a.attrs["href"]
            for a in soup.findAll("a", attrs={'href': re.compile(r"^http://www.lamarea.com/2\d+/\d+/\d+/.*")})]
    urls = sorted(list(set(urls)))

    for url in urls:
        slp = (count / 10) + (count % 2)
        time.sleep(slp)

        response = br.open(url)
        apsoup = bs4.BeautifulSoup(response.read(), "lxml")
        t = apsoup.find("h2", attrs={'id': "titulo"})
        e = None  # apsoup.find("div",attrs={'class': "except"})
        c = apsoup.find("div", attrs={'class': "shortcode-content"})

        if t and c:
            if count == 1:
                h = soup.new_tag("h1")
                h.string = "APÉNDICES"
                soup.body.append(h)
            mkr = "ap" + str(count)
            t.attrs.clear()
            t.attrs["id"] = mkr

            for aurl in soup.findAll("a", attrs={'href': url}):
                aurl.attrs.clear()
                aurl.attrs["href"] = "#" + mkr

            articulo = soup.new_tag("article")

            ap = soup.new_tag("p")
            ia = apsoup.select("div.article-controls div.infoautor a")
            if len(ia) > 0:
                ia = ia[0]
                ia.attrs.clear()
                ia.name = "strong"
                ap.append(ia)
            cf = apsoup.find("div", attrs={'class': "calendar-full"})
            if cf:
                ap.append(" " + sp.sub(" ", cf.get_text()).strip())
            if len(sp.sub(" ", ap.get_text().strip())) > 0:
                articulo.append(ap)
            if e:
                articulo.append(e)
            for i in apsoup.findAll("div", attrs={'class': "article-photo"}):
                nex = i.next_sibling
                while nex and not nex.name:
                    nex = nex.next_sibling
                if nex and nex.name == "div" and "class" in nex.attrs and "article-photo-foot" in nex.attrs["class"]:
                    nex.name = "p"
                    i.append(nex)
                img = i.find("img")
                if not img or "src" not in img.attrs or img.attrs["src"] == "":
                    i.extract()
                    continue
                articulo.append(i)

            articulo.append(c)

            for img in articulo.findAll("img", attrs={'src': re.compile(r".*banner.*")}):
                img.extract()
            limpiar(articulo)
            limpiar2(articulo)
            for p in articulo.select("p"):
                if p.find("img") and p.find("span"):
                    div = soup.new_tag("div")
                    for img in p.findAll("img"):
                        div.append(img)
                    s = soup.new_tag("p")
                    s.string = p.get_text()
                    div.append(s)
                    p.replaceWith(div)
            for div in articulo.select("div"):
                if "style" not in div.attrs and not div.select("img"):
                    div.unwrap()

            soup.body.append(t)
            soup.body.append(articulo)
            count = count + 1

            print url

for img in soup.findAll("img"):
    src = img.attrs["src"]
    img.attrs.clear()
    img.attrs["src"] = src
    div = img.parent
    if div.name == "div":
        div.attrs.clear()
        if div.find("p"):
            div.attrs["class"] = "imagen conpie"
        else:
            div.attrs["class"] = "imagen sinpie"

for n in soup.findAll(text=lambda text: isinstance(text, bs4.Comment)):
    n.extract()
for div in soup.findAll("div"):
    if len(div.findAll(heads)) > 0 or (len(div.select(" > *")) == 0 and len(sp.sub("", div.get_text().strip())) == 0):
        div.unwrap()

h = get_html(soup)
with open("lamarea_" + str(numero) + ".html", "wb") as file:
    file.write(h.encode('utf8'))
