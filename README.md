*[La Marea](http://www.lamarea.com/)* ofrece a sus [subscriptores](http://www.lamarea.com/kiosco) su edición mensual en formato papel, pdf o blog online, pero actualmente no dispone de una versión en epub.

Por ello, este script genera un epub a partir de la versión del blog online.

Para crear el epub se requieren tener un fichero de configuración en formato YAML
que contenga un documento por cada número de La Marea que se quiera pasar a epub.

Ejemplo:

```yaml
num: 47
usuario: ******
clave: ********
portada: http://www.revista.lamarea.com/wp-content/uploads/2017/02/LM_Portada047_RGB.jpg
titulo: Nos dejan sin palabras
fecha: 2017-02-22
---
num: 48
usuario: ******
clave: ********
portada: http://www.revista.lamarea.com/wp-content/uploads/2017/04/LM_Portada048.jpg
fecha: 2017-03-29
titulo: Los plasmas del IBEX35
```

y luego lanzar el script `lamareaepub.py` ( ver `lamareaepub.py --help` para más detalles )

Esto básicamente generará un fichero `lamarea_XX.html` y `lamarea_XX.epub`, por cada número.

Este script hace uso del comando `miepub`, que es a su vez un script que se puede obtener en https://github.com/s-nt-s/miepub (requiere [`pandoc 1.19.2`](https://github.com/jgm/pandoc/releases) o mayor).
