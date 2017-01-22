# -*- coding: utf-8 -*-
 
import sys
from mechanize import Browser
import bs4
import re
import argparse

parser = argparse.ArgumentParser(description='Genera un html único a partir de www.revista.lamarea.com')
parser.add_argument("url", help="Url completa al número de la revista")
parser.add_argument('--usuario', help='Usuario de acceso a www.revista.lamarea.com', required=True)
parser.add_argument('--clave', help='Contraseña de acceso www.revista.lamarea.com', required=True)
parser.add_argument('--apendices', help='Genera un capítulo de apendices con los conetenidos de los enlaces a www.lamarea.com', required=False, action="store_true")

arg = parser.parse_args()

rPortada = re.compile(r"http://www.revista.lamarea.com/\S*?/wp-content/uploads/\S*?/\S*?Portada\S*?.jpg", re.IGNORECASE)
tab=re.compile("^", re.MULTILINE)
sp=re.compile("\s+", re.UNICODE)
tag_concat=['u','ul','ol','i','em','strong']
tag_round=['u','i','em','span','strong', 'a']
tag_trim=['li', 'th', 'td', 'div','caption','h[1-6]']
tag_right=['p']
sp=re.compile("\s+", re.UNICODE)
nb=re.compile("^\s*\d+\.\s+", re.UNICODE)

urls=["#", "javascript:void(0)"]
editorial=None

br = Browser()

def get_html(soup):
    h=unicode(soup)
    r=re.compile("(\s*\.\s*)</a>", re.MULTILINE|re.DOTALL|re.UNICODE)
    h=r.sub("</a>\\1",h)
    for t in tag_concat:
        r=re.compile("</"+t+">(\s*)<"+t+">", re.MULTILINE|re.DOTALL|re.UNICODE)
        h=r.sub("\\1",h)
    for t in tag_round:
        r=re.compile("(<"+t+">)(\s+)", re.MULTILINE|re.DOTALL|re.UNICODE)
        h=r.sub("\\2\\1",h)
        r=re.compile("(<"+t+" [^>]+>)(\s+)", re.MULTILINE|re.DOTALL|re.UNICODE)
        h=r.sub("\\2\\1",h)
        r=re.compile("(\s+)(</"+t+">)", re.MULTILINE|re.DOTALL|re.UNICODE)
        h=r.sub("\\2\\1",h)
    for t in tag_trim:
        r=re.compile("(<"+t+">)\s+", re.MULTILINE|re.DOTALL|re.UNICODE)
        h=r.sub("\\1",h)
        r=re.compile("\s+(</"+t+">)", re.MULTILINE|re.DOTALL|re.UNICODE)
        h=r.sub("\\1",h)
    for t in tag_right:
        r=re.compile("\s+(</"+t+">)", re.MULTILINE|re.DOTALL|re.UNICODE)
        h=r.sub("\\1",h)
        r=re.compile("(<"+t+">) +", re.MULTILINE|re.DOTALL|re.UNICODE)
        h=r.sub("\\1",h)
    r=re.compile(r"\s*(<meta[^>]+>)\s*", re.MULTILINE|re.DOTALL|re.UNICODE)
    h=r.sub(r"\n\1\n",h)
    r=re.compile(r"\n\n+", re.MULTILINE|re.DOTALL|re.UNICODE)
    h=r.sub(r"\n",h)
    return h

def get_tpt(title,img):
	soup=bs4.BeautifulSoup('''
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
	''' % (title,img)
	,'lxml')
	return soup

def get_enlaces(soup,hjs=[]):
	wpb=soup.find("div", attrs={'class': "wpb_wrapper"})
	if not wpb:
		return hjs
	noes = wpb.select("div.eltd-post-info-date a")
	hrefs = wpb.select("h1 a, h2 a, h3 a, h4 a, h5 a, h6 a") + wpb.select("a")
	for h in hrefs:
		if h in noes:
			continue
		href=h.attrs["href"]
		txth=h.get_text().strip()
		if len(txth)>0 and href not in urls and href not in hjs:
			hjs.append(h)
	return hjs

class Pagina:
	def __init__(self, titulo, url, tipo=None):
		self.titulo = titulo
		self.url = url
		self.tipo = tipo
		self.hijas = []
		self.articulo = None
		self.autor = None
		if url == editorial:
			self.titulo = "Editorial: " + titulo
			self.tipo = 999
		urls.append(url)

	def add(self,a, tipo=None,hjs=[]):
		url=a.attrs["href"].strip()
		txt=a.get_text().strip()
		if len(txt)==0 or len(url)==0 or url in urls:
			return
		art=None
		if not tipo:
			page = br.open(url)
			soup = bs4.BeautifulSoup(page.read(),"lxml")
			art=soup.find("article")
			if not art:
				hjs = get_enlaces(soup,hjs)
				if len(hjs) == 0:
					return
		p = Pagina(txt, url, tipo)
		p.articulo=art
		if p.tipo == 999:
			lamarea.hijas.insert(0,p)
		else:
			self.hijas.append(p)
		for a in hjs:
			p.add(a)

	def __unicode__(self):
		ln=self.titulo
		ln=ln+"\n"+self.url
		st=""
		for h in self.hijas:
			st=st+"\n"+unicode(h)
		st=tab.sub("  ",st)
		return ln+st
	
	def soup(self,soup=None,nivel=1):
		if self.articulo:
			if self.tipo == 999:
				self.articulo.find("img").extract()
				self.articulo.find("img").extract()
			self.articulo.attrs["nivel"]=str(nivel)
			return self.articulo
		if self.tipo==0:
			soup=get_tpt(self.titulo, self.url)

		div=soup.new_tag("div")
		for i in self.hijas:
			h=soup.new_tag("h"+str(nivel))
			h.string=i.titulo
			div.append(h)
			div.append(i.soup(soup,nivel+1))
		
		if self.tipo==0:
			soup.body.append(div)
			div.unwrap()
			return soup
		return div

page = br.open(arg.url)

portada=rPortada.search(page.read()).group()
numero=int(portada.split('_')[-1].split('.')[0])

lamarea=Pagina("La Marea #"+str(numero), portada, 0)

br.select_form(name="login-form")
br.form["log"] = arg.usuario
br.form["pwd"] = arg.clave
page=br.submit()

soup=bs4.BeautifulSoup(page.read(),"lxml")
editorial=soup.find("a",text="Editorial")
if editorial:
	editorial=editorial.attrs["href"]
dossier=soup.find("h2", text=re.compile(r"^\s*DOSSIER\s*.+", re.MULTILINE|re.DOTALL|re.UNICODE))
if dossier:
	dossier=sp.sub(" ",dossier.get_text()).strip()

for li in soup.select("#menu-header > li"):
	i=li.find("a")
	if (dossier and sp.sub(" ",i.get_text()).strip().upper()=="DOSSIER"):
		i.string=dossier
	hijas=[]
	for a in li.select("ul li a"):
		hijas.append(a)
	lamarea.add(i,None,hijas)

for a in get_enlaces(soup):
	lamarea.add(a)

print unicode(lamarea)

soup=lamarea.soup()

block=["h1","h2","h3","h4","h5","h6","p","div","table","article"]
inline=["span","strong","b"]

for div in soup.select("div.eltd-post-image-area"):
	div.extract()

for i in soup.findAll(["b"]):
	i.unwrap()

for s in soup.findAll("span"):
	if "style" not in s.attrs:
		s.unwrap()

for i in soup.findAll(block):
	if i.find("img"):
		continue
	txt=sp.sub("",i.get_text().strip())
	if len(txt)==0 or txt==".":
		i.extract()
	else:
		i2=i.select(" > "+i.name)
		if len(i2)==1:
			txt2=sp.sub("",i2[0].get_text().strip())
			if txt==txt2:
				i.unwrap()

for i in soup.findAll(inline):
	txt=sp.sub("",i.get_text().strip())
	if len(txt)==0:
		i.unwrap()

for i in soup.findAll(block + inline):
	i2=i.select(" > "+i.name)
	if len(i2)==1:
		txt=sp.sub("",i.get_text().strip())
		txt2=sp.sub("",i2[0].get_text().strip())
		if txt==txt2:
			i.unwrap()

autores=[]
autores_nombres=[]

for art in soup.select("article"):
	art.find("div").unwrap()
	cabs=[]
	nivel = int(art.attrs["nivel"])
	for n in range(1,7):
		cab=art.select("h"+str(n))
		if len(cab)>0:
			cabs.append(cab)
	for cab in cabs:
		for h in cab:
			h.name="h"+str(nivel)
		nivel=nivel+1

	auth=art.find("div", attrs={'class': "saboxplugin-wrap"})
	if not auth:
		auth=art.find("div", attrs={'class': "saboxplugin-authorname"})
	if auth:
		aut=sp.sub(" ", auth.get_text().strip())
		if aut=="La Marea":
			auth.extract()
		else:
			autores.append(auth)
			for a in auth.select("a"):
				a.name="strong"
				a.attrs.clear()
				aut=sp.sub(" ", a.get_text().strip())
				if len(aut)>0 and aut == aut.upper():
					aut = aut.title()
					a.string=aut
			for b in auth.select("br"):
				b.extract()

	for img in art.select("a > img"):
		a=img.parent
		if len(a.get_text().strip())==0:
			img.attrs["src"]=a.attrs["href"]
			a.unwrap()

for n in soup.body.findAll(["h1","h2","h3","h4","h5","h6","p","div","span","strong","b","i","article"]):
	style=None
	if "style" in n.attrs:
		style=n.attrs["style"]
	elif n.name=="span":
		n.unwrap()
		continue
	n.attrs.clear()
	if style:
		n.attrs["style"]=style

for img in soup.findAll("img"):
	src=img.attrs["src"]
	img.attrs.clear()
	img.attrs["src"]=src
	div=img.parent
	if div.name=="div":
		div.attrs.clear()
		if div.find("p"):
			div.attrs["class"]="imagen conpie"
		else:
			div.attrs["class"]="imagen sinpie"
			
for auth in autores:
	if auth.find("img"):
		auth.attrs["class"]="autor conimg".split()
	else:
		auth.attrs["class"]="autor sinimg".split()

autores_nombres=sorted(list(set([s.get_text() for s in soup.body.select("div.autor strong")])))
for a in autores_nombres:
	meta=soup.new_tag("meta")
	meta.attrs["name"]="DC.contributor"
	meta.attrs["content"]=a
	soup.head.append(meta)
'''
if lamarea.hijas[0].tipo == 999:
	edi=sp.sub(" ",lamarea.hijas[0].articulo.get_text()).strip().replace("\"","'")
	meta=soup.new_tag("meta")
	meta.attrs["name"]="DC.description"
	meta.attrs["content"]=edi
	soup.head.append(meta)
'''

if arg.apendices:
	apendices=soup.new_tag("div")
	for a in soup.findAll("a",attrs={'href': re.compile(r"^http://www.lamarea.com/2\d+/\d+/\d+/.*")}):
		url=a.attrs["href"]
		response = br.open(url)
		apsoup = bs4.BeautifulSoup(response.read(),"lxml")
		t=apsoup.find("h2",attrs={'id': "titulo"})
		e=apsoup.find("div",attrs={'class': "except"})
		c=apsoup.find("div",attrs={'class': "shortcode-content"})
	
		if t and c:
			t.attrs.clear()
			apendices.append(t)
			ap=soup.new_tag("p")
			ia=apsoup.select("div.article-controls div.infoautor a")
			if len(ia)>0:
				ia=ia[0]
				ia.attrs.clear()
				ia.name="strong"
				ap.append(ia)
			cf=apsoup.find("div",attrs={'class': "calendar-full"})
			if cf:
				ap.append(" "+sp.sub(" ",cf.get_text()).strip())
			if len(sp.sub(" ",ap.get_text().strip()))>0:
				apendices.append(ap)
			if e:
				apendices.append(e)
			for i in apsoup.findAll("div",attrs={'class': re.compile(r"^article-photo.*")}):
				apendices.append(i)
			apendices.append(c)
			print "> " +url

	if len(apendices.contents)>0:
		for img in apendices.findAll("img",attrs={'src': re.compile(".*banner.*")}):
			img.extract()
	
		h=soup.new_tag("h1")
		h.string="Apendices"
		soup.body.append(h)
		soup.body.append(apendices)


h = get_html(soup)
with open("lamarea_"+str(numero)+".html", "wb") as file:
	file.write(h.encode('utf8'))
