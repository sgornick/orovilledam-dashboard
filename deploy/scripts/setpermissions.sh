#!/bin/bash
# Make sure to not run from the wrong directory.
test -d '../../deploy/scripts' || { echo "The script $(basename $0) should be run only from the [project]/deploy/scripts directory."; exit 1; }
# Group user is www-data, which is what gunicorn is configured to use.
sudo chown -R $USER:www-data ../../
chmod -R o-rwx ../../
find ../../ ! -path "*/venv" ! -path "*/venv/*" ! -path "*/__pycache__" ! -path "*/__pycache__/*" ! -name "*.sock" -exec chmod g-rwx {} \;
chmod -R u+rw ../../
find ../../ -type d -exec chmod u+x {} \;
find ../../ -type d ! -path "*/.git*" -exec chmod g+rx {} \;
chmod g+w ../../
chmod g+w ../../web_site
chmod g+w ../../web_site/data
chmod --silent g+rw ../../web_site/data/*.json
chmod -R g+r ../../web_site/static
chmod -R g+r ../../web_site/templates
chmod -f g+r ../../gunicorn-*.conf || true
chmod ug+rx ./*
find ../../ -type f -name "*.sh" ! -path "*/venv/*" -exec chmod u+x {} \;
find ../../ -type f -name "*.py" ! -path "*/venv/*" -exec chmod g+r {} \;
(cd ../..; find . -exec stat -c "%a %n" {} \; |sort -k 2)
