from CvPythonExtensions import *
import cPickle as pickle # В Python 2.4 (на котором работает Civ 4) используется cPickle

gc = CyGlobalContext()

# Civ4 даёт ОДИН строковый слот на объект Game - CyGame().ScriptData.
# Если разные системы мода пишут туда напрямую через pickle.dumps(...)/setScriptData(...),
# они стирают данные друг друга при полной перезаписи (так столкнулись счётчик нюков
# и климат). Это единственное место в коде мода, которое должно трогать этот слот -
# любая новая система читает/пишет через getValue/setValue/updateValues ниже, вместо
# своего pickle по CyGame().ScriptData.

def loadAll():
    raw = gc.getGame().getScriptData()
    if raw == "":
        return {}
    data = pickle.loads(raw)
    if isinstance(data, list):  # формат до перехода на словарь: [iNumNukesFired]
        return {"numNukes": data[0]}
    return data

def _save(data):
    gc.getGame().setScriptData(pickle.dumps(data))

def getValue(key, default=None):
    return loadAll().get(key, default)

def setValue(key, value):
    data = loadAll()
    data[key] = value
    _save(data)

def updateValues(mapping):
    data = loadAll()
    data.update(mapping)
    _save(data)
