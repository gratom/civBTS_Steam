## Utopia
## "Smart growth": per-city switches that ask the game to automatically hold
## off population growth (via the stock EMPHASIZE_AVOID_GROWTH checkbox)
## whenever happiness and/or health are running too tight.
##
## Same architecture as CvAutoSpecialistManager - read that file's header for
## the full reasoning:
##  - flags live in CvCity.ScriptData (per-city, saved/synced with the city)
##  - toggling goes through CyMessageControl().sendModNetMessage() /
##    CvEventManager.onModNetMessage(), never written directly from a click
##  - the actual city-state check and enforcement runs from onEndPlayerTurn,
##    which the engine already runs identically on every client
##
## One extra wrinkle here: flipping EMPHASIZE_AVOID_GROWTH has no direct
## Python setter (only AI_isEmphasize is exposed, not AI_setEmphasize) - the
## only way to change it is CyMessageControl().sendDoTask(TASK_SET_EMPHASIZE),
## the same call the stock checkbox itself sends. That call is tagged with
## *this client's own* active player, so it's only guarded to fire when the
## local active player actually owns the city - on every other client it
## would silently fail city-ownership validation anyway, but checking here
## avoids relying on that and keeps the intent obvious.

from CvPythonExtensions import *
import cPickle as pickle

gc = CyGlobalContext()

SCRIPT_DATA_KEY_HAPPY = "AutoGrowConsiderHappy"
SCRIPT_DATA_KEY_HEALTH = "AutoGrowConsiderHealth"
MOD_MESSAGE_TOGGLE_GROWTH_FLAG = 7262	# tag for CyMessageControl().sendModNetMessage / onModNetMessage

g_iEmphasizeAvoidGrowth = None

def _getEmphasizeAvoidGrowth():
	# Looked up lazily (not at module import time) - the XML info database
	# may not be loaded yet when this module first gets imported.
	global g_iEmphasizeAvoidGrowth
	if g_iEmphasizeAvoidGrowth is None:
		g_iEmphasizeAvoidGrowth = gc.getInfoTypeForString("EMPHASIZE_AVOID_GROWTH")
	return g_iEmphasizeAvoidGrowth


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


def isConsiderHappy(pCity):
	return bool(_loadCityData(pCity).get(SCRIPT_DATA_KEY_HAPPY, False))


def isConsiderHealth(pCity):
	return bool(_loadCityData(pCity).get(SCRIPT_DATA_KEY_HEALTH, False))


def requestToggleHappy(pCity):
	'Call this from UI click handlers.'
	bNewValue = not isConsiderHappy(pCity)
	CyMessageControl().sendModNetMessage(MOD_MESSAGE_TOGGLE_GROWTH_FLAG, pCity.getOwner(), pCity.getID(), 0, int(bNewValue))


def requestToggleHealth(pCity):
	'Call this from UI click handlers.'
	bNewValue = not isConsiderHealth(pCity)
	CyMessageControl().sendModNetMessage(MOD_MESSAGE_TOGGLE_GROWTH_FLAG, pCity.getOwner(), pCity.getID(), 1, int(bNewValue))


def handleNetMessage(iData2, iData3, iData4, iData5):
	'Called from CvEventManager.onModNetMessage on every client once the toggle message is replayed.'
	pPlayer = gc.getPlayer(iData2)
	pCity = pPlayer.getCity(iData3)
	if pCity:
		data = _loadCityData(pCity)
		if iData4 == 0:
			data[SCRIPT_DATA_KEY_HAPPY] = bool(iData5)
		else:
			data[SCRIPT_DATA_KEY_HEALTH] = bool(iData5)
		_saveCityData(pCity, data)
		CyInterface().setDirty(InterfaceDirtyBits.CityScreen_DIRTY_BIT, True)


def enforceCity(pCity):
	bConsiderHappy = isConsiderHappy(pCity)
	bConsiderHealth = isConsiderHealth(pCity)

	if (not bConsiderHappy) and (not bConsiderHealth):
		return

	bShouldRestrict = False

	if bConsiderHappy and (pCity.happyLevel() <= pCity.unhappyLevel(0)):
		bShouldRestrict = True

	if bConsiderHealth and (pCity.goodHealth() <= pCity.badHealth(False)):
		bShouldRestrict = True

	iEmphasizeAvoidGrowth = _getEmphasizeAvoidGrowth()
	bCurrentlyRestricted = pCity.AI_isEmphasize(iEmphasizeAvoidGrowth)

	if (bShouldRestrict != bCurrentlyRestricted) and (pCity.getOwner() == gc.getGame().getActivePlayer()):
		CyMessageControl().sendDoTask(pCity.getID(), TaskTypes.TASK_SET_EMPHASIZE, iEmphasizeAvoidGrowth, -1, bShouldRestrict, False, False, False)


def enforcePlayer(iPlayer):
	'Call this once per player turn (onEndPlayerTurn) - never from a UI click.'
	pPlayer = gc.getPlayer(iPlayer)

	(pCity, iter) = pPlayer.firstCity(false)
	while pCity:
		enforceCity(pCity)
		(pCity, iter) = pPlayer.nextCity(iter, false)
