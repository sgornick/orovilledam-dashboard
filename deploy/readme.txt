        Instructions for deploying orovilledam.org in the cloud.

Hosted on a VPS (Digital Ocean Droplet).

Access these instructions if need help with any of these steps.
  http://blog.marksteve.com/deploy-a-flask-application-inside-a-digitalocean-droplet

************************************************************************
Add/Update orovilledam.org software:

   Ensure dependencies:
      Ubuntu 14.04:
      $ sudo apt-get install python3.4-venv

      Ubuntu 16.04 or later:
      $ sudo apt-get install python3-venv

    Clone repo and create virtual environment:
      $ sudo test

      $ export SERVER_NAME=orovilledam.org
      $ cd /var/www
      $ sudo mkdir $SERVER_NAME
      $ sudo chown $USER:www-data $SERVER_NAME
      $ git clone https://github.com/sgornick/orovilledam.org.git $SERVER_NAME
      $ cd $SERVER_NAME
      $ python3 -m venv venv
      $ source venv/bin/activate
      $ pip install --upgrade pip
      $ pip install -r deploy/requirements.txt
      $ deactivate

    Configure instance variables.
      If supporting /latest to return an image of the latest gauge readings,
        that uses a cloud service PhantomJSCloud.com, and an API key is needed.
      $ cd /var/www/orovilledam.org/web_site/instance
      $ cp config-template.py config.py
      $ vi config.py
         And replace the value for the API key using yours from PhantomJSCloud.com

'  Update file ownership and permissions.
      $ ( cd /var/www/$SERVER_NAME/deploy/scripts; ./setpermissions.sh )

  Configure gunicorn - Using Supervisor (e.g., for Ubuntu 14.04):
      NOTE - systemd is not used, thus the following are not used:
       - deploy/orovilledam.service

      $ cd /var/www/orovilledam.org

      $ cp deploy/gunicorn-orovilledam.conf .
      $ sudo chown :www-data gunicorn-orovilledam.conf
      $ chmod g+r gunicorn-orovilledam.conf
      $ sudo cp deploy/supervisor-orovilledam.conf /etc/supervisor/conf.d
      $ sudo supervisorctl reload

  Configure gunicorn - Using systemd (e.g., for Ubuntu 16.04):
      NOTE - Supervisor is not used, thus the following are not used:
       - deploy/gunicorn-orovilledam.conf

      $ cd /var/www/orovilledam.org

      $ sudo cp deploy/orovilledam.service /etc/systemd/system/
      $ sudo chmod go+r /etc/systemd/system/orovilledam.service
      $ sudo systemctl daemon-reload
      $ sudo systemctl start orovilledam
      $ sudo systemctl enable orovilledam

'  Configure Nginx
      $ cd /var/www/orovilledam.org
      $ sudo cp deploy/nginx.conf /etc/nginx/sites-available/orovilledam.org.conf
      $ sudo ln -s /etc/nginx/sites-available/orovilledam.org.conf /etc/nginx/sites-enabled
      $ sudo service nginx reload
      $ exit

   Configure Cron
      $ sudo vi /etc/crontab

      Append the following (which will run the refreshgauges once a minute).

      */1 * * * * www-data /var/www/orovilledam.org/deploy/scripts/refreshgauges.sh

************************************************************************
