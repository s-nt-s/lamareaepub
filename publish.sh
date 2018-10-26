#!/bin/bash
cd out
scp -r htpasswd lamarea.nginx pilan:www/
ssh -t pilan '
sudo cp www/htpasswd/*.htpasswd /etc/nginx/htpasswd/
sudo mv www/lamarea.nginx /etc/nginx/sites-available/
sudo systemctl restart nginx
'
scp -r index.html epub html portada rec pilan:www/private/lamarea
