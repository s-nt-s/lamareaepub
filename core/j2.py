import os

from jinja2 import Environment, FileSystemLoader


def my_date(d):
    y, m, _ = d.split("-", 2)
    m=int(m)
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
    return m+"-"+y[2:]

def my_title(t):
    _, t = t.split(": ",1)
    return t

class Jnj2():

    def __init__(self, origen, destino, pre=None, post=None):
        self.j2_env = Environment(
            loader=FileSystemLoader(origen), trim_blocks=True)
        self.j2_env.filters['my_date'] = my_date
        self.j2_env.filters['my_title'] = my_title
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
