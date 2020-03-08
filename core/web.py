import sys
import bs4
from urllib.parse import urljoin, urlparse
import requests
import time
import re
from .util import get_config
import json

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


def buildSoup(root, source):
    soup = bs4.BeautifulSoup(source, "lxml")
    for n in soup.findAll(["img", "form", "a", "iframe", "frame", "link", "script"]):
        attr = "href" if n.name in ("a", "link") else "src"
        if n.name == "form":
            attr = "action"
        val = n.attrs.get(attr)
        if val and not (val.startswith("#") or val.startswith("javascript:")):
            val = urljoin(root, val)
            n.attrs[attr] = val
    return soup

class Web:
    def __init__(self, refer=None, verify=True):
        self.s = requests.Session()
        self.s.headers = default_headers
        self.response = None
        self.soup = None
        self.form = None
        self.refer = refer
        self.verify = verify

    def get(self, url, **kargv):
        if self.refer:
            self.s.headers.update({'referer': self.refer})
        if kargv:
            self.response = self.s.post(url, data=kargv, verify=self.verify)
        else:
            self.response = self.s.get(url, verify=self.verify)
        self.refer = self.response.url
        self.soup = bs4.BeautifulSoup(self.response.content, "lxml")
        for n in self.soup.findAll(["img", "form", "a", "iframe", "frame", "link", "script"]):
            attr = "href" if n.name in ("a", "link") else "src"
            if n.name == "form":
                attr = "action"
            val = n.attrs.get(attr)
            if val and not (val.startswith("#") or val.startswith("javascript:")):
                val = urljoin(url, val)
                n.attrs[attr] = val
        return self.soup

    def prepare_submit(self, slc, silent_in_fail=False, **kargv):
        data = {}
        self.form = self.soup.select_one(slc)
        if silent_in_fail and self.form is None:
            return None, None
        for i in self.form.select("input[name]"):
            name = i.attrs["name"]
            data[name] = i.attrs.get("value")
        for i in self.form.select("select[name]"):
            name = i.attrs["name"]
            slc = i.select_one("option[selected]")
            slc = slc.attrs.get("value") if slc else None
            data[name] = slc
        data = {**data, **kargv}
        action = self.form.attrs.get("action")
        action = action.rstrip() if action else None
        if action is None:
            action = self.response.url
        return action, data

    def submit(self, slc, silent_in_fail=False, **kargv):
        action, data = self.prepare_submit(slc, silent_in_fail=silent_in_fail, **kargv)
        if silent_in_fail and not action:
            return None
        return self.get(action, **data)

    def val(self, slc):
        n = self.soup.select_one(slc)
        if n is None:
            return None
        v = n.attrs.get("value", n.get_text())
        v = v.strip()
        return v if v else None

class LoginException(Exception):
    pass

class MareaSpider(Web):
    TP_LISTA=1
    TP_PAGINA=2

    def __init__(self, cnf, *args, **kargv):
        super().__init__(*args, **kargv)
        if isinstance(cnf, str):
            config_file, num = cnf.rsplit(":", 1)
            config = get_config(config_file)
            cnf = config[int(num)]
        self.cnf = cnf
        self.root = cnf.url.split("://", 1)[1].lower()
        self.get(cnf.url)
        self.submit("#login-form",
            log=cnf.usuario,
            pwd=cnf.clave
        )
        self.error = self.val(".login-error")
        self.enlaces = None
        self.orden = 0

    def isLocal(self, url):
        url = url.split("://", 1)[1].lower()
        return ".php" not in url and url.startswith(self.root)

    def add_enlace(self, url, **kargv):
        if not self.isLocal(url):
            return
        url = url.rstrip("/")
        kargv = {k:v for k,v in kargv.items() if v is not None}
        if "categoria" in kargv:
            kargv["categoria"] = kargv["categoria"].lower()
        if url in self.enlaces:
            keys = self.enlaces[url].keys()
            self.enlaces[url].update({k:v for k,v in kargv.items() if k not in keys})
        else:
            self.orden = self.orden + 1
            kargv["orden"] = self.orden
            self.enlaces[url]=kargv

    def print_enlaces(self):
        print(json.dumps(self.enlaces, indent=4))

    def create_map(self):
        cat_menu=[]
        self.enlaces = {}
        a = self.soup.find("a", text="EDITORIAL")
        if a:
            url = a.attrs["href"]
            self.add_enlace(url, categoria="editorial")
        for c in self.soup.select("#menu-header > li"):
            a = c.find("a")
            url = a.attrs["href"].rstrip("/")
            cat = url.rsplit("/")[-1].lower()
            if cat not in cat_menu:
                cat_menu.append(cat)
            self.add_enlace(url, categoria=cat, tipo=MareaSpider.TP_LISTA)
            for a in c.select("ul a"):
                url = a.attrs["href"]
                tit = a.get_text().strip()
                self.add_enlace(url, categoria=cat)
        for cat in cat_menu:
            re_cat = re.compile(".*/category/"+cat+"/.*", re.IGNORECASE)
            for a in self.soup.findAll("a", href=re_cat):
                url = a.attrs["href"]
                self.add_enlace(url, categoria=cat, tipo=MareaSpider.TP_LISTA)
