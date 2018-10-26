import os

from jinja2 import Environment, FileSystemLoader


def my_date(dt):
    y, m, d = dt.split("-", 2)
    d, _ = d.split("T", 1)
    d=int(d)
    m=int(m)
    y=int(y[2:])
    if d>18:
        m=m+1
    if m == 13:
        m = 1
        y = y + 1
    if m==1:
        m="ene"
    elif m==2:
        m="feb"
    elif m==3:
        m="mar"
    elif m==4:
        m="abr"
    elif m==5:
        m="may"
    elif m==6:
        m="jun"
    elif m==7:
        m="jul"
    elif m==8:
        m="ago"
    elif m==9:
        m="sep"
    elif m==10:
        m="oct"
    elif m==11:
        m="nov"
    elif m==12:
        m="dic"
    return m+"-"+str(y)

def my_title(t):
    _, t = t.split(": ",1)
    return t

def bytes_to_mbs(b):
    if isinstance(b, str):
        return b
    mb = b / 1024 / 1024
    mb = "%.1f MB" % mb
    mb = mb.replace(".0","")
    return mb

class Jnj2():

    def __init__(self, origen, destino, pre=None, post=None):
        self.j2_env = Environment(
            loader=FileSystemLoader(origen), trim_blocks=True)
        self.j2_env.filters['my_date'] = my_date
        self.j2_env.filters['my_title'] = my_title
        self.j2_env.filters['bytes_to_mbs'] = bytes_to_mbs
        self.destino = destino
        self.pre = pre
        self.post = post

    def save(self, template, destino=None, parse=None, **kwargs):
        if destino is None:
            destino = template
        out = self.j2_env.get_template(template)
        html = out.render(**kwargs)
        if self.pre:
            html = self.pre(html, **kwargs)
        if parse:
            html = parse(html, **kwargs)
        if self.post:
            html = self.post(html, **kwargs)

        destino = self.destino + destino
        directorio = os.path.dirname(destino)

        if not os.path.exists(directorio):
            os.makedirs(directorio)

        with open(destino, "wb") as fh:
            fh.write(bytes(html, 'UTF-8'))
        return html
