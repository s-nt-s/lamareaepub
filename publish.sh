#!/bin/bash
cd out
scp -r index.html *.xml favicon.* portada rec pilan:www/private/lamarea
rsync -r epub pilan:www/private/lamarea
scp -r htpasswd lamarea.nginx pilan:www/
ssh -t pilan '
sudo cp www/htpasswd/*.htpasswd /etc/nginx/htpasswd/
sudo mv www/lamarea.nginx /etc/nginx/sites-available/
sudo systemctl restart nginx
'
