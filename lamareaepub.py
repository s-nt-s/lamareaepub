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

rPortada = re.compile(
    r"http://www.revista.lamarea.com/\S*?\bwp-content/uploads/\S*?/\S*?Portada\S*?.jpg", re.IGNORECASE)
tab = re.compile("^", re.MULTILINE)
sp = re.compile("\s+", re.UNICODE)
nonumb = re.compile("\D+")
re_apendices = re.compile(r"^http://www.lamarea.com/2\d+/\d+/\d+/.*")
re_scribd = re.compile(r"^(https://www.scribd.com/embeds/\d+)/.*")
re_youtube = re.compile(r"https://www.youtube.com/embed/(.+?)\?.*")

tag_concat = ['u', 'ul', 'ol', 'i', 'em', 'strong']
tag_round = ['u', 'i', 'em', 'span', 'strong', 'a']
tag_trim = ['li', 'th', 'td', 'div', 'caption', 'h[1-6]']
tag_right = ['p']
sp = re.compile("\s+", re.UNICODE)
nb = re.compile("^\s*\d+\.\s+", re.UNICODE)

heads = ["h1", "h2", "h3", "h4", "h5", "h6"]
block = heads + ["p", "div", "table", "article"]
inline = ["span", "strong", "b", "del"]

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
        phref = urlparse(href)
        if phref.path and phref.path.startswith("/tag/"):
            continue
        txth = h.get_text().strip()
        if len(txth) > 0 and href not in urls and href not in hjs:
            hjs.append(h)
    return hjs

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
            rutas(url, soup)
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
        for i in range(len(self.hijas) - 1):
            if self.hijas[i].titulo.lower() in ("anuncios breves", u"publicidad ética"):
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
            h.attrs["id"] = i.url
            div.append(h)
            div.append(i.soup(soup, nivel + 1))

        if self.tipo == 0:
            soup.body.append(div)
            div.unwrap()
            return soup
        return div


class Apendice:
    
    def __init__(self, url):
        response = br.open(url)
        self.soup = bs4.BeautifulSoup(response.read(), "lxml")
        self.titulo = self.soup.find("h2", attrs={'id': "titulo"})
        self.content = self.soup.find("div", attrs={'class': "shortcode-content"})
        self.url = url
        self.articulo = None
        if self.titulo and self.content:
            rutas(url, self.content)
            self.urls = [a.attrs["href"] for a in self.content.findAll("a", attrs={'href': re_apendices})]
            self.urls = sorted(list(set(self.urls)))
            self.titulo.attrs.clear()
            self.titulo.attrs["id"] = url

    def isok(self):
        return self.titulo and self.content

    def build_articulo(self, soup):
        if self.articulo:
            return self.articulo
        
        self.articulo = soup.new_tag("article")
        ap = soup.new_tag("p")
        
        ia = self.soup.select("div.article-controls div.infoautor a")
        if len(ia) > 0:
            ia = ia[0]
            ia.attrs.clear()
            ia.name = "strong"
            ap.append(ia)
        cf = self.soup.find("div", attrs={'class': "calendar-full"})
        if cf:
            ap.append(" " + sp.sub(" ", cf.get_text()).strip())
        if len(sp.sub(" ", ap.get_text().strip())) > 0:
            self.articulo.append(ap)
        e = None  # self.soup.find("div",attrs={'class': "except"})
        if e:
            self.articulo.append(e)
        for i in self.soup.findAll("div", attrs={'class': "article-photo"}):
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
            self.articulo.append(i)

        self.articulo.append(a.content)

        for img in self.articulo.findAll("img", attrs={'src': re.compile(r".*(banner|LM_aportacion_.*\.gif).*", re.IGNORECASE)}):
            img.extract()
        img = self.soup.select("div.tagimagen img")
        src=img[0].attrs.get("src", None) if len(img)>0 else None
        if src:
            for img in self.articulo.findAll("img", attrs={'src': src}):
                img.extract()

        limpiar(self.articulo)
        limpiar2(self.articulo, self.url)
        for p in self.articulo.select("p"):
            if p.find("img") and p.find("span"):
                div = soup.new_tag("div")
                for img in p.findAll("img"):
                    div.append(img)
                s = soup.new_tag("p")
                s.string = p.get_text()
                div.append(s)
                p.replaceWith(div)
        for div in self.articulo.select("div"):
            if "style" not in div.attrs and not div.select("img"):
                div.unwrap()

        return self.articulo


page = br.open(arg.url)

if not arg.portada:
    arg.portada = rPortada.search(page.read()).group()


br.select_form(name="login-form")
br.form["log"] = arg.usuario
br.form["pwd"] = arg.clave
page = br.submit()

soup = bs4.BeautifulSoup(page.read(), "lxml")

info = soup.find("div",attrs={'id': "info"})
if not arg.num:
    n=info.find("p",attrs={'class': "numero"}) if info else None
    numb=None
    if n:
        numb = nonumb.sub("", n.get_text())
    if not numb or not numb.isdigit():
        imagenportada = arg.portada.split('/')[-1].split('.')[0]
        numb = nonumb.sub("", imagenportada)
    if not numb or not numb.isdigit():
        numb = nonumb.sub("", arg.usuario)
    arg.num = int(numb)

if not arg.fecha and info:
    p = info.find("p").get_text()
    p = sp.sub(" ", p).strip().lower()
    m, y = p.split(" ")
    m = meses.index(m[0:3])+1
    arg.fecha = "%s-%02d" % (y, m)

lamarea = Pagina("La Marea #" + str(arg.num), arg.portada, 0)

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
    hcab = ["h" + str(i) for i in range(nivel, 7)]
    for n in range(1, 7):
        cab = art.select("h" + str(n))
        if len(cab) > 0:
            cabs.append(cab)
    for cab in cabs:
        for h in cab:
            h.name = "h" + str(nivel)
        nivel = nivel + 1
    cambios = len(hcab)
    while cambios > 0:
        cambios = 0
        ct = []
        for h in art.findAll(hcab):
            c = int(h.name[1])
            aux = [x for x in ct if x < c]
            if len(aux) > 0:
                a = aux[-1] + 1
                if a < c:
                    cambios += 1
                    h.name = "h" + str(a)
            ct.append(c)

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
'''
if arg.fecha:
    meta = soup.new_tag("meta")
    meta.attrs["name"] = "DC.date"
    meta.attrs["content"] = arg.fecha
    soup.head.append(meta)
'''
autores_nombres = sorted(
    list(set([sp.sub(" ",s.get_text()) for s in soup.body.select("div.autor strong")])))
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
    urls = [a.attrs["href"]
            for a in soup.findAll("a", attrs={'href': re_apendices})]
    urls = sorted(list(set(urls)))

    count = 0
    apendices = []
    print "  APÉNDICES, buscando\r",
    sys.stdout.flush()
    while count<len(urls):
        print "  APÉNDICES, buscando" + ('.' * (count +1)) + "\r",
        sys.stdout.flush()
        slp = (count / 10) + (count % 2)
        time.sleep(slp)
        a = Apendice(urls[count])
        if a.isok():
            apendices.append(a)
            if arg.recursivo:
                for u in a.urls:
                    if u not in urls:
                        urls.append(u)
        count += 1

    if len(apendices)==0:
        print "  APÉNDICES, no hay   " + (' ' * (count +1))
    else:
        print "  APÉNDICES           " + (' ' * (count +1))
        h = soup.new_tag("h1")
        h.string = "APÉNDICES"
        soup.body.append(h)
        apendices = sorted(apendices, key=lambda k: k.url) 
        for a in apendices:
            soup.body.append(a.titulo)
            soup.body.append(a.build_articulo(soup))
            print "    " + a.titulo.get_text()
            print "    " + a.url

count = 0
for h in soup.findAll(heads, attrs={'id': re.compile(r"^http.*")}):
    url = h.attrs["id"]
    del h.attrs["id"]
    links = soup.findAll("a", attrs={'href': url})
    if len(links)>0:
        count += 1
        h.attrs["id"] = "mrk" + str(count)
        mkr = "#" + h.attrs["id"]
        for a in links:
            a.attrs["href"] = mkr
            if "target" in a.attrs:
                del a.attrs["target"]

for img in soup.findAll("img"):
    src = img.attrs["src"]
    img.attrs.clear()
    img.attrs["src"] = src
    div = img.parent
    if div.name == "div":
        div.attrs.clear()
        p = div.find("p")
        if p:
            div.name = "figure"
            p.name = "figcaption"
            #div.attrs["class"] = "imagen conpie"
        else:
            div.attrs["class"] = "imagen sinpie"

for n in soup.findAll(text=lambda text: isinstance(text, bs4.Comment)):
    n.extract()
for div in soup.findAll("div"):
    if len(div.findAll(heads)) > 0 or (len(div.select(" > *")) == 0 and len(sp.sub("", div.get_text().strip())) == 0):
        div.unwrap()

h = get_html(soup)
with open("lamarea_" + str(arg.num) + ".html", "wb") as file:
    file.write(h.encode('utf8'))
