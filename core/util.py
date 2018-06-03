# -*- coding: utf-8 -*-

import sys
import bs4
import re
import argparse
import time
from urllib.parse import urlparse, urljoin
from os.path import splitext

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

meses = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

def get_html(soup):
    h = str(soup)
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
        if "id" not in n.attrs and n.name == "span":
            n.unwrap()
            continue
        _id = n.attrs.get("id", None)
        attrs = {k:v for k, v in n.attrs.items() if k.startswith("data-") or k in ("style", )}
        if _id and n.name in heads and _id.startswith("http"):
            attrs["id"] = _id
        n.attrs = attrs

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

def build_soup(url, response):
    text = response.text
    
    if url == "https://www.lamarea.com/2018/04/03/siete-puntos-de-friccion-en-el-informe-de-los-expertos-en-transicion-energetica/":
        rpl = ' <b class="unwrapme"><span class="unwrapme">'
        text = text.replace('<b>1.Aprobación no unánime: <span style="font-weight: 400;">', '<strong>1.Aprobación no unánime</strong>:'+rpl)
        text = text.replace('<b>3.Gas: <span style="font-weight: 400;">', '<strong>3.Gas</strong>:'+rpl)
        text = text.replace('<b>5.Renovables: <span style="font-weight: 400;">', '<strong>5.Renovables</strong>:'+rpl)
        text = text.replace('<b>6.Impuestos: <span style="font-weight: 400;">', '<strong>6.Impuestos</strong>:'+rpl)
        text = text.replace('<strong>7.Interconexiones:</strong>', '<strong>7.Interconexiones</strong>:')

    soup = bs4.BeautifulSoup(text, "lxml")
    
    for unwrapme in soup.select(".unwrapme"):
        unwrapme.unwrap()
    for extractme in soup.select(".extractme"):
        extractme.extract()

    return soup
