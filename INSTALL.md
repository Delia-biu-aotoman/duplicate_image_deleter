mkvirtualenv p3
pip install -r requirements.txt

OS X:
This is needed for GTK

```brew install pygobject3 --with-python3```

Get it working in a virtualenv:
ln -s /usr/local/lib/python3.6/site-packages/gi /Users/karl/.virtualenvs/p3/lib/python3.5/site-packages

brew install gtk+3
brew install pygobject3
