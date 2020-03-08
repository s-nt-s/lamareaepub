#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse
import yaml
import sys
import os
from bunch import Bunch
from core.lamareahtml import LaMarea, tune_html_for_epub
from core.util import get_html, get_config
from core.indice import build_indice
from core.j2 import Jnj2, my_date
from core.tratar_imgs import tune_epub
from glob import glob
import re
from subprocess import run, DEVNULL, call, check_output
import os
import tempfile
import epub_meta
import base64
import crypt
import textwrap
import bs4
import requests
from datetime import datetime
import json
from feedgen.feed import FeedGenerator
import pytz

parser = argparse.ArgumentParser(description='Genera html único y epub a partir de www.revista.lamarea.com')
parser.add_argument("--num", nargs='*', type=int, help="Números a generar (por defecto son todos)")
parser.add_argument("config", nargs='?', help="Fichero de configuración en formato Yaml", default="lamarea.yml")

arg = parser.parse_args()

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

config = get_config(arg.config)
cnfnum = sorted([(k, v) for k,v in config.items() if isinstance(k, int) and (arg.num is None or k in arg.num)])

for num, cnf in cnfnum:
    build_indice(cnf)
