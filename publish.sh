#!/bin/bash
cd out
scp -r index.html favicon.* portada rec epub pilan:www/private/lamarea
scp -r htpasswd lamarea.nginx pilan:www/
ssh -t pilan '
sudo cp www/htpasswd/*.htpasswd /etc/nginx/htpasswd/
sudo mv www/lamarea.nginx /etc/nginx/sites-available/
sudo systemctl restart nginx
'
