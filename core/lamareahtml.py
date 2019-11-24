# -*- coding: utf-8 -*-

import requests
import bs4
import re
import sys
import time
from urllib.parse import urljoin, urlparse
from .util import get_tpt, get_title, limpiar, limpiar2, rutas, heads, tab, rPortada, sp, re_apendices, build_soup, get_html
from datetime import datetime
import pytz

default_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:54.0) Gecko/20100101 Firefox/54.0',
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Expires": "Thu, 01 Jan 1970 00:00:00 GMT",
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

def fixDate(dt):
    try:
        return pytz.UTC.localize(dt)
    except:
        return dt

def add_class(node, class_name):
    cl = node.attrs.get("class", "")
    if isinstance(cl, str):
        cl = (cl +" "+class_name).strip()
    else:
        cl.append(class_name)
    node.attrs["class"] = cl

def get_enlaces(soup, hjs=None, urls=None):
    if hjs is None:
        hjs = []
    if urls is None:
        urls = []
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

class Pagina:

    def __init__(self, root, titulo, url, tipo=None):
        self.root = root
        self.titulo = titulo
        self.url = urljoin(self.root.config.url, url)
        self.tipo = tipo
        self.hijas = []
        self.articulo = None
        self.autor = None
        if url == self.root.editorial:
            self.tipo = 999
            if titulo.lower() != "editorial":
                self.titulo = "Editorial: " + titulo
        self.root.urls.append(url)

    @property
    def contenedor(self):
        '''
        if self.tipo == 999:
            return "editorial"
        '''
        if self.titulo.lower() in ("anuncios breves", "publicidad ética"):
            return "anuncios"
        return None


    def add(self, a, tipo=None, hjs=[]):
        url = a.attrs["href"].strip()
        url = urljoin(self.root.config.url, url)
        txt = a.get_text().strip()
        if len(txt) == 0 or len(url) == 0 or url in self.root.urls:
            return
        soup = None
        art = None
        if not tipo:
            soup = self.root.get(url)
            art = soup.find("article")
            if not art:
                hjs = get_enlaces(soup, hjs=hjs, urls=self.root.urls)
                if len(hjs) == 0:
                    return
        p = Pagina(self.root, txt, url, tipo)
        p.articulo = art
        if p.tipo == 999:
            self.root.page.hijas.insert(0, p)
            if soup and p.titulo.lower() == "editorial":
                p.titulo = "Editorial: " + soup.find("h1").get_text()
        else:
            self.hijas.append(p)
        for a in hjs:
            p.add(a)

    def __str__(self):
        ln = self.titulo
        ln = ln + "\n" + self.url
        st = ""
        self.reordenar_hijas()
        for h in self.hijas:
            st = st + "\n" + str(h)
        st = tab.sub("  ", st)
        return ln + st

    def reordenar_hijas(self):
        for i in range(len(self.hijas) - 1):
            if self.hijas[i].titulo.lower() in ("anuncios breves", "publicidad ética"):
                self.hijas.append(self.hijas.pop(i))
                return

    def soup(self, soup=None, nivel=1):
        if self.articulo:
            self.articulo.attrs["data-src"] = self.url
            if self.tipo == 999:
                # La imagen del editorial es la portada
                for img in self.articulo.findAll("img"):
                    img.extract()
                '''
                if len(self.articulo.select("div.eltd-post-image img")) > 0:
                    self.articulo.find("img").extract()
                    self.articulo.find("img").extract()
                '''
            self.articulo.attrs["nivel"] = str(nivel)
            return self.articulo

        if self.tipo == 0:
            soup = get_tpt(self.titulo, self.url, self.root.config.num)

        div = soup.new_tag("div")
        for i in self.hijas:
            h = soup.new_tag("h" + str(nivel))
            h.string = i.titulo
            h.attrs["id"] = i.url
            self.root.heads.append((h, i.url))

            if i.contenedor:
                contenedor = soup.new_tag("contenedor")
                contenedor.attrs["id"]=i.contenedor
                contenedor.attrs["class"]="contenedor"
                contenedor.append(h)
                contenedor.append(i.soup(soup, nivel + 1))
                div.append(contenedor)
            else:
                div.append(h)
                div.append(i.soup(soup, nivel + 1))

        if self.tipo == 0:
            soup.body.append(div)
            div.unwrap()
            return soup
        return div

class LaMarea():

    def __init__(self, config):
        self.config = config
        self.urls = []
        self.heads = []
        self.s =  requests.Session()
        self.s.headers = default_headers
        if not config.portada:
            r = self.s.get(config.url)
            m = rPortada.search(r.text)
            if m:
                config.portada = m.group(1).replace("\\/", "/")
        r = self.s.post(config.url,data={
            "is_custom_login": 1,
            "log": config.usuario,
            "pwd": config.clave,
            "submit": "Acceder"
        })
        soup = bs4.BeautifulSoup(r.content, "lxml")

        info = soup.find("div",attrs={'id': "info"})

        self.editorial = soup.find("a", text="Editorial")
        if self.editorial:
            self.editorial = self.editorial.attrs["href"]
        self.dossier = soup.find("h2", text=re.compile(r"^\s*DOSSIER\s*.+", re.MULTILINE | re.DOTALL | re.UNICODE))
        if self.dossier:
            self.dossier = sp.sub(" ", self.dossier.get_text()).strip()

        tit = "La Marea #" + str(config.num)
        if config.titulo:
            tit = tit + ": " + config.titulo

        self.page = Pagina(self, tit, config.portada, 0)

        for li in soup.select("#menu-header > li"):
            i = li.find("a")
            if (self.dossier and sp.sub(" ", i.get_text()).strip().upper() == "DOSSIER"):
                i.string = self.dossier
            hijas = []
            for a in li.select("ul li a"):
                hijas.append(a)
            self.page.add(i, None, hijas)

        for a in get_enlaces(soup, urls=self.urls):
            self.page.add(a)

        self.soup = self.load_soup()

    def get(self, url):
        r = self.s.get(url)
        soup = build_soup(url, r)
        return soup

    def load_soup(self):
        soup = self.page.soup()

        for div in soup.select("div.eltd-post-image-area"):
            div.extract()

        limpiar(soup)

        autores = []
        autores_nombres = []

        for art in soup.select("article"):
            #art.find("div").unwrap()
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

            auth = art.select("div.saboxplugin-wrap, div.saboxplugin-authorname")
            if len(auth)>0:
                auth = auth[0]
                aut = sp.sub(" ", auth.get_text().strip())
                if aut == "La Marea":
                    auth.extract()
                else:
                    autores.append(auth)
                    for a in auth.select("a"):
                        a.name = "strong"
                        a.attrs.clear()
                        aut = sp.sub(" ", a.get_text()).strip()
                        if len(aut) > 0 and aut == aut.upper():
                            aut = aut.title()
                            a.string = aut
                    for b in auth.select("br"):
                        b.extract()

        limpiar2(soup)
        for a in soup.findAll("article"):
            n1 = a.select(":scope > *")[0]
            if n1.name[0]=="h":
                n1.name="p"

        for auth in autores:
            if auth.find("img"):
                auth.attrs["class"] = "autor conimg".split()
            else:
                auth.attrs["class"] = "autor sinimg".split()
            #print (auth)
            nb = auth.find("strong")
            dv = nb.parent
            if dv and dv.name == "div" and dv != auth and sp.sub(" ", nb.get_text()).strip() == sp.sub(" ", dv.get_text()).strip():
                dv.attrs["class"] = "nombre"

        if self.config.fecha:
            meta = soup.new_tag("meta")
            meta.attrs["name"] = "DC.date"
            meta.attrs["content"] = self.config.fecha
            soup.head.append(meta)

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

        print (str(self.page))

        urls = [a.attrs["href"]
                for a in soup.findAll("a", attrs={'href': re_apendices})]
        urls = sorted(list(set(urls)))

        count = 0
        apendices = []
        spaces = 1
        print ("  APÉNDICES, buscando", end="\r")
        sys.stdout.flush()
        while count<len(urls):
            print (" " * (30 + spaces), end="\r")
            print ("  APÉNDICES, buscando [%s]" % (count,), end="\r")
            sys.stdout.flush()
            slp = (count / 10) + (count % 2)
            time.sleep(slp)
            a_url = urls[count]
            spaces = len(a_url)
            print ("  APÉNDICES, buscando [%s] %s" % (count, a_url), end="\r")
            a = get_apendice(a_url)
            if a and a.isok():
                apendices.append(a)
                if False: #arg.recursivo:
                    for u in a.urls:
                        if u not in urls:
                            urls.append(u)
            count += 1

        print (" " * (30 + spaces), end="\r")
        if len(apendices)==0:
            print ("  APÉNDICES, no hay   " + (' ' * (count +1)))
        else:
            print ("  APÉNDICES           " + (' ' * (count +1)))

            contenedor = soup.new_tag("contenedor")
            contenedor.attrs["id"]="apendices"
            contenedor.attrs["class"]="contenedor"

            h = soup.new_tag("h1")
            h.string = "APÉNDICES"
            contenedor.append(h)
            apendices = sorted(apendices, key=lambda k: fixDate(k.date))
            for a in apendices:
                self.heads.append((a.titulo, a.url))
                contenedor.append(a.titulo)
                contenedor.append(a.articulo)
                print ("    " + a.titulo.get_text())
                print ("    " + a.url)

            soup.body.append(contenedor)

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
                    a.attrs["data-href"] = a.attrs["href"]
                    a.attrs["href"] = mkr
                    a.attrs["class"] = "local"
                    if "target" in a.attrs:
                        del a.attrs["target"]

        for img in soup.findAll("img"):
            src = img.attrs["src"]
            img.attrs.clear()
            img.attrs["src"] = src
            div = img.parent
            if div.name == "div" and not div.find(heads):
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
            if len(div.findAll(heads)) > 0 or (len(div.select(":scope > *")) == 0 and len(sp.sub("", div.get_text().strip())) == 0):
                div.unwrap()

        if self.config.portada:
            div = soup.new_tag("div")
            div.attrs["class"] ="noepub portada"
            img = soup.new_tag("img")
            img.attrs["src"] = self.config.portada
            div.append(img)
            soup.body.insert(0, div)

        for h, url in self.heads:
            a = soup.new_tag("a")
            a.attrs["class"] ="noepub"
            a.attrs["href"] = url
            a.attrs["target"] = "_blank"
            a.string = "#"
            h.insert(0, a)

        for contenedor in soup.findAll("contenedor"):
            contenedor.name = "div"

        for img in soup.findAll("img"):
            if img.attrs["src"] in self.config.graficas:
                add_class(img, "grafica")
            else:
                art = img.find_parent("article")
                if art and not art.get_text().strip():
                    print(img.attrs["src"])
                    add_class(img, "grafica")

        for p in soup.findAll(["p", "figure"]):
            img = p.findAll("img")
            if len(img)==1:
                txt = sp.sub(" ", p.get_text()).strip()
                if len(txt)==0:
                    img = img[0]
                    add_class(img, "imagensola")
                    p.name = "p"

        for div in soup.select("article > div"):
            if not div.attrs:
                div.unwrap()

        return soup

class Apendice:
    def __init__(self, url):
        r = requests.get(url, headers=default_headers)
        self.url = url
        self.soup = build_soup(url, r)
        self.shortlink = None
        self.api = None
        self.js = {}
        aux = self.soup.select("link[rel=shortlink]")
        if len(aux)>0:
            self.shortlink = aux[0].attrs["href"]
            self.id = self.shortlink.split("=")[-1]
            self.id = int(self.id)
            aux = self.soup.select('link[rel="https://api.w.org/"]')
            if len(aux)>0:
                self.api = aux[0].attrs["href"]+"wp/v2/posts/%s" % self.id
                r = requests.get(self.api, headers=default_headers)
                self.js = r.json()
        self.titulo = self.js.get("title", {}).get("rendered", None)
        if self.titulo:
            self.titulo = bs4.BeautifulSoup("<h2>"+self.titulo.strip()+"</h2>", "html.parser").find("h2")
        self.content = self.js.get("content", {}).get("rendered", None)
        if self.content:
            self.content = build_soup(self.url, self.content)
        self.date = self.js.get("date", None)
        if self.date is not None:
            self.date = datetime.strptime(self.date, '%Y-%m-%dT%H:%M:%S')
        else:
            dt = self.soup.find("meta", attrs={"property":"article:published_time"})
            if dt:
                dt = dt.attrs["content"]
                self.date = datetime.strptime(dt[:22] + dt[23:], '%Y-%m-%dT%H:%M:%S%z') # 2018-04-02T11:37:52+00:00

    def isok(self):
        if not self.date and not self.titulo or not self.content:
            return False
        if self.content.find("strong", text=re.compile(r"^\s*Art\S+culo\s+incluido\s+en\s+el\s+dossier.*")):
            return False
        return True

    @property
    def urls(self):
        urls = [a.attrs["href"] for a in self.content.findAll("a", attrs={'href': re_apendices})]
        return sorted(set(self.urls))

    @property
    def articulo(self):
        if not self.isok():
            return None
        self.titulo.attrs.clear()
        self.titulo.attrs["id"] = self.url
        return self.get_articulo()

    def get_articulo(self):
        return None

class ApendiceApuntes(Apendice):

    def __init__(self, url):
        Apendice.__init__(self, url)
        self.titulo = self.soup.find("h1")
        self.content = self.soup.find("div", attrs={'class': "entry-content"})

    def get_articulo(self):
        articulo = self.soup.new_tag("article")
        articulo.attrs["data-src"] = self.url
        ap = self.soup.new_tag("p")

        ia = self.soup.select("span.entry-author-name")
        if len(ia) > 0:
            ia = ia[0]
            ia.attrs.clear()
            ia.name = "strong"
            ap.append(ia)

        ap.append(" " + self.date.strftime("%d-%m-%Y"))
        if len(sp.sub(" ", ap.get_text().strip())) > 0:
            articulo.append(ap)
        e = None #self.soup.find("div",attrs={'class': "except"})
        if e:
            txt1 = re.sub(r"\W", "", sp.sub(" ", e.get_text()).strip())
            txt2 = re.sub(r"\W", "", sp.sub(" ", self.content.get_text()).strip())
            if txt1 not in txt2:
                articulo.append(e)
        img = self.soup.findAll("figure.single-post-image")
        if len(img)>0:
            img=img[0]
            articulo.append(img)

        articulo.append(self.content)

        limpiar(articulo)
        limpiar2(articulo)

        return articulo

class ApendiceMarea(Apendice):

    def __init__(self, url):
        Apendice.__init__(self, url)

    def get_articulo(self):
        articulo = self.soup.new_tag("article")
        articulo.attrs["data-src"] = self.url
        ap = self.soup.new_tag("p")

        ia = self.soup.select("div.article-info div.author-name a")
        if len(ia) > 0:
            ia = ia[0]
            ia.attrs.clear()
            ia.name = "strong"
            ap.append(ia)

        ap.append(" " + self.date.strftime("%d-%m-%Y"))
        if len(sp.sub(" ", ap.get_text().strip())) > 0:
            articulo.append(ap)
        img = self.soup.select("figure.single-post-image")
        if len(img)>0:
            img=img[0]
            articulo.append(img)

        articulo.append(self.content)

        limpiar(articulo)
        limpiar2(articulo)

        return articulo

class ClimaticaMarea(Apendice):

    def __init__(self, url):
        Apendice.__init__(self, url)
        if not self.titulo:
            self.titulo = self.soup.find("h1")
            self.titulo.name = "h1"
            self.titulo.attrs.clear()
        if not self.content:
            self.content = self.soup.find("div", attrs={"class":"contenido"})

    def get_articulo(self):
        articulo = self.soup.new_tag("article")
        articulo.attrs["data-src"] = self.url
        ap = self.soup.new_tag("p")

        ia = self.soup.select("span.author a")
        if len(ia) > 0:
            ia = ia[0]
            ia.attrs.clear()
            ia.name = "strong"
            ap.append(ia)

        ap.append(" " + self.date.strftime("%d-%m-%Y"))
        if len(sp.sub(" ", ap.get_text().strip())) > 0:
            articulo.append(ap)
        img = self.soup.select("div.imagen-destacada.superior figure")
        if len(img)>0:
            img=img[0]
            articulo.append(img)

        articulo.append(self.content)

        limpiar(articulo)
        limpiar2(articulo)

        return articulo

def get_apendice(url):
    dom = urlparse(url).netloc
    if dom in ("www.climatica.lamarea.com", "climatica.lamarea.com"):
        return ClimaticaMarea(url)
    if dom in ("www.lamarea.com", "lamarea.com"):
        return ApendiceMarea(url)
    if dom == "apuntesdeclase.lamarea.com":
        return ApendiceApuntes(url)
    return None


def tune_html_for_epub(html_file, *args):
    with open(html_file, "r") as f:
        soup = bs4.BeautifulSoup(f.read(), "lxml")

    extract = ".noepub"
    if args:
       extract = extract +  ", #" + (", #".join(args))

    for noepup in soup.select(extract):
        noepup.extract()

    for contenedor in soup.select(".contenedor"):
        contenedor.unwrap()

    for a in soup.findAll("a", attrs={'href': re.compile(r"^#mrk\d+")}):
        mrk = a.attrs["href"][1:]
        if not soup.find(heads, attrs={'id': mrk}):
            a.attrs["href"] = a.attrs["data-href"]
            del a.attrs["class"]

    for a in soup.findAll("a"):
        href = a.attrs["href"]
        if not href.startswith("#"):
            dom = urlparse(href).netloc
            dom = re.sub("^www\.|:\d+$", "", dom)
            if dom not in a.get_text():
                small = soup.new_tag("small")
                small.string = "[" + dom + "]"
                a.append(" ")
                a.append(small)

    for n in soup.select("*"):
        if n.attrs:
            n.attrs = {k:v for k, v in n.attrs.items() if not k.startswith("data-")}

    out = html_file +".tmp.html"
    h = get_html(soup)
    with open(out, "w") as file:
        file.write(h)
    return out
