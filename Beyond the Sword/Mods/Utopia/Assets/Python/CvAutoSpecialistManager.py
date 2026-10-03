## Utopia
## Per-city "keep this specialist at 0" flags, stored in CvCity.ScriptData.
##
## The flag must never be written directly from a UI click: that code path
## only runs on the clicking client, and in network multiplayer every client
## simulates the full game independently, so a direct write here would only
## exist on one machine and desync the rest. Instead the click sends a
## CyMessageControl().sendModNetMessage(), which is replayed identically on
## every client and lands in CvEventManager.onModNetMessage -> handleNetMessage
## below, which is where the actual write happens.
##
## Removing the unwanted specialists is safe to do directly, because
## enforcePlayer() is only ever called from onEndPlayerTurn, which the engine
## already runs identically on every client as part of that player's normal
## turn processing (same reasoning as onCityGrowth/onCityDoTurn).

from CvPythonExtensions import *
import cPickle as pickle

gc = CyGlobalContext()

SCRIPT_DATA_KEY = "AutoRemoveSpecialists"
MOD_MESSAGE_TOGGLE_AUTO_REMOVE = 7261	# tag for CyMessageControl().sendModNetMessage / onModNetMessage


def _loadCityData(pCity):
	szData = pCity.getScriptData()
	if not szData:
		return {}
	try:
		data = pickle.loads(szData)
	except Exception:
		return {}
	if not isinstance(data, dict):
		return {}
	return data


def _saveCityData(pCity, data):
	pCity.setScriptData(pickle.dumps(data))


def getAutoRemoveList(pCity):
	data = _loadCityData(pCity)
	return list(data.get(SCRIPT_DATA_KEY, []))


def isAutoRemoveSpecialist(pCity, iSpecialist):
	return iSpecialist in getAutoRemoveList(pCity)


def _setAutoRemoveSpecialist(pCity, iSpecialist, bValue):
	data = _loadCityData(pCity)
	aiList = list(data.get(SCRIPT_DATA_KEY, []))

	if bValue:
		if iSpecialist not in aiList:
			aiList.append(iSpecialist)
	else:
		if iSpecialist in aiList:
			aiList.remove(iSpecialist)

	data[SCRIPT_DATA_KEY] = aiList
	_saveCityData(pCity, data)


def requestToggle(pCity, iSpecialist):
	'Call this from UI click handlers. Sends a synced net message instead of writing ScriptData directly.'
	bNewValue = not isAutoRemoveSpecialist(pCity, iSpecialist)
	CyMessageControl().sendModNetMessage(MOD_MESSAGE_TOGGLE_AUTO_REMOVE, pCity.getOwner(), pCity.getID(), iSpecialist, int(bNewValue))


def handleNetMessage(iData2, iData3, iData4, iData5):
	'Called from CvEventManager.onModNetMessage on every client once the toggle message is replayed.'
	pPlayer = gc.getPlayer(iData2)
	pCity = pPlayer.getCity(iData3)
	if pCity:
		_setAutoRemoveSpecialist(pCity, iData4, bool(iData5))
		CyInterface().setDirty(InterfaceDirtyBits.CitizenButtons_DIRTY_BIT, True)


def enforceCity(pCity):
	for iSpecialist in getAutoRemoveList(pCity):
		iCount = pCity.getSpecialistCount(iSpecialist)
		if iCount > 0:
			pCity.alterSpecialistCount(iSpecialist, -iCount)


def enforcePlayer(iPlayer):
	'Call this once per player turn (onEndPlayerTurn) - never from a UI click.'
	pPlayer = gc.getPlayer(iPlayer)

	(pCity, iter) = pPlayer.firstCity(false)
	while pCity:
		enforceCity(pCity)
		(pCity, iter) = pPlayer.nextCity(iter, false)
