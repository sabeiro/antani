#host set up apache
sudo yum -y install httpd php libapache2-mod-wsgi python-dev
sudo a2enmod rewrite proxy_http proxy_ajp deflate headers proxy_balancer proxy_connect proxy_html wsgi
#ubuntu
cd /etc/apache/sites-available/
sudo cp $LAV_DIR/antani_apache.conf . & sudo a2ensite antani_apache.conf & sudo service apache2 restart
#centos
GROUP_WWW=apache
sudo mkdir /etc/httpd/sites-available /etc/httpd/sites-enabled
sudo cp ~/antani/antani_apache.conf /etc/httpd/sites-available/
sudo ln -s /etc/httpd/sites-available/antani_apache.conf /etc/httpd/conf.d/antani_apache.conf
sudo groupadd $GROUP_WWW
sudo usermod -a -G $GROUP_WWW apache
sudo usermod -a -G $GROUP_WWW httpd
sudo usermod -a -G $GROUP_WWW $USER
sudo usermod -a -G apache $USER
sudo ln -s ~/antani/ /var/www/antani
sudo chown -R $USER:$GROUP_WWW /var/www/antani
sudo chown $USER:$GROUP_WWW ~
sudo chown $USER:$GROUP_WWW ~/antani/
sudo chown -R $USER:$GROUP_WWW ~/antani/antani_viz
cd /var/www/antani
find . -type d -exec chmod 2775 {} \;
find . -type f -exec chmod 0664 {} \;
sudo find . -type d -exec chmod 775 {} \;
sudo find . -type f -exec chmod 664 {} \;
sudo chgrp -R $GROUP_WWW /var/www/html
sudo find /var/www/html -type d -exec chmod g+rx {} +
sudo find /var/www/html -type f -exec chmod g+r {} +
sudo chown -R $USER /var/www/html/
sudo find /var/www/html -type d -exec chmod u+rwx {} +
sudo find /var/www/html -type f -exec chmod u+rw {} +
sudo find /var/www/html -type d -exec chmod g+s {} +
#sudo chmod -R o-rwx /var/www/html/
sudo systemctl restart httpd.service
curl $SERVER/antani
curl $SERVER/ant
sudo mkdir /var/run/celery
sudo chown $USER /var/run/celery/
sudo vim /etc/httpd/conf.d/userdir.conf
sudo setsebool -P httpd_enable_homedirs on
sudo restorecon -R /home
mkdir /home/$USER/public_html
chmod 711 /home/$USER
chmod 755 /home/$USER/public_html
vi ./public_html/index.html 
