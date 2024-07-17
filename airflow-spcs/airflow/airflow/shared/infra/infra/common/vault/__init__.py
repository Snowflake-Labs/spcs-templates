import os
for fileName in os.listdir(os.path.dirname(__file__)):
    if fileName.endswith(".py") and not fileName.startswith("__"):
        modName = fileName[:-3]   # strip .py at the end
        exec('from .' +  modName + ' import *')