*[La Marea](http://www.lamarea.com/)* ofrece a sus [subscriptores](http://www.lamarea.com/kiosco/#!/D011-La-Marea-n%C2%BA-47/p/80130070/category=5355224) su edición mensual en formato papel, pdf o blog online, pero actualmente no dispone de una versión en epub.

Por ello, este script genera un epub a partir de la versión del blog online.

Para crear el epub se requieren dos pasos:

1- Lanzar `lamareaepub.py` de la siguiente manera:

```console
$ python lamareaepub.py --usuario USER --clave PASS URL
```

Donde USER y PASS son el usuario y clave que *La Marea* facilita a sus subscriptores para cada número, y URL es la dirección del blog online donde se alberga dicho número.

Esto generara un fichero `lamarea_XX.html`, donde `XX` es el número de esa edición, con el contenido preparado para ser pasado a epub.

Opcionalmente, si se ejecuta con el comando `--apendices` se generará un capitulo adicional llamado *APÉNDICES* que incluirá los artículos de http://www.lamarea.com/ que hubieran sido referenciados en el número.

2- Lanzar `miepub`

`miepub` es un script que se puede obtener aquí https://github.com/s-nt-s/miepub (requiere [`pandoc 1.19.2`](https://github.com/jgm/pandoc/releases) o mayor) y que ejecutandolo así:

```console
$ miepub lamarea_XX.html
```

creará el epub con el nombre `lamarea_XX.epub`
