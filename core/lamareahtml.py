# -*- coding: utf-8 -*-

import requests
import bs4
import re
import sys
import time
from urllib.parse import urljoin, urlparse
from .util import get_tpt, get_title, limpiar, limpiar2, rutas, heads, tab, rPortada, sp, re_apendices, build_soup, get_html

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
            rutas(url, soup)
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
            soup = get_tpt(self.titulo, self.url)

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
                        aut = sp.sub(" ", a.get_text()).strip()
                        if len(aut) > 0 and aut == aut.upper():
                            aut = aut.title()
                            a.string = aut
                    for b in auth.select("br"):
                        b.extract()

        limpiar2(soup)
        for a in soup.findAll("article"):
            n1 = a.select("> *")[0]
            if n1.name[0]=="h":
                n1.name="p"

        for auth in autores:
            if auth.find("img"):
                auth.attrs["class"] = "autor conimg".split()
            else:
                auth.attrs["class"] = "autor sinimg".split()
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
        print ("  APÉNDICES, buscando", end="\r")
        sys.stdout.flush()
        while count<len(urls):
            print ("  APÉNDICES, buscando" + ('.' * (count +1)), end="\r")
            sys.stdout.flush()
            slp = (count / 10) + (count % 2)
            time.sleep(slp)
            a = Apendice(urls[count])
            if a.isok():
                apendices.append(a)
                if False: #arg.recursivo:
                    for u in a.urls:
                        if u not in urls:
                            urls.append(u)
            count += 1

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
            apendices = sorted(apendices, key=lambda k: k.url) 
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
            if len(div.findAll(heads)) > 0 or (len(div.select(" > *")) == 0 and len(sp.sub("", div.get_text().strip())) == 0):
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
                cl = img.attrs.get("class", "")
                if isinstance(cl, str):
                    cl = (cl +" grafica").strip()
                else:
                    cl.append("grafica")
                img.attrs["class"] = cl

        return soup

class Apendice:
    
    def __init__(self, url):
        r = requests.get(url, headers=default_headers)
        self.soup = build_soup(url, r)
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
            self.articulo = self.build_articulo()

    def isok(self):
        return self.titulo and self.content

    def build_articulo(self):
        self.articulo = self.soup.new_tag("article")
        self.articulo.attrs["data-src"] = self.url
        ap = self.soup.new_tag("p")
        
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

        self.articulo.append(self.content)

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
                div = self.soup.new_tag("div")
                for img in p.findAll("img"):
                    div.append(img)
                s = self.soup.new_tag("p")
                s.string = p.get_text()
                div.append(s)
                p.replaceWith(div)
        for div in self.articulo.select("div"):
            if "style" not in div.attrs and not div.select("img"):
                div.unwrap()

        return self.articulo

def tune_html_for_epub(html_file, *args):
    with open(html_file, "r") as f:
        soup = bs4.BeautifulSoup(f.read(), "lxml")

    extract = ".noepub"
    if args:
       extract +  ", #" + (", #".join(args))

    for noepup in soup.select(extract):
        noepup.extract()
        
    for contenedor in soup.select(".contenedor"):
        contenedor.unwrap()

    for a in soup.findAll("a", attrs={'href': re.compile(r"^#mrk\d+")}):
        mrk = a.attrs["href"][1:]
        if not soup.find(heads, attrs={'id': mrk}):
            a.attrs["href"] = a.attrs["data-href"]
            del a.attrs["class"]

    for n in soup.select("*"):
        if n.attrs:
            n.attrs = {k:v for k, v in n.attrs.items() if not k.startswith("data-")}

    out = html_file +".tmp.html"
    h = get_html(soup)
    with open(out, "w") as file:
        file.write(h)
    return out
            
