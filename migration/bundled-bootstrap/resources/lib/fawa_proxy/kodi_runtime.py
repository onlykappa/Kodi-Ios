import xbmc as _xbmc
def log(*args, **kwargs):
    pass
def __getattr__(name):
    return getattr(_xbmc, name)
