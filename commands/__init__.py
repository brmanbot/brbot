# from os.path import dirname, basename, isfile
# import glob
# import importlib

# modules = glob.glob(dirname(__file__) + "/*.py")
# __all__ = [
#     importlib.import_module("commands." + basename(f)[:-3])
#     for f in modules
#     if isfile(f) and not f.endswith("__init__.py")
# ]