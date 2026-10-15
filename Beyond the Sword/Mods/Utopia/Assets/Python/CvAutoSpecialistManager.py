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


NUM_CITY_PLOTS = 21	# home plot (index 0) + the 20 plots in the city's work radius
CITY_HOME_PLOT = 0


def _specialistRoom(pCity, iSpecialist):
	'How many more of this specialist type the city will currently accept.'
	if gc.getPlayer(pCity.getOwner()).isSpecialistValid(iSpecialist):
		return 999	# a building/civic override lifts the max count entirely
	return max(0, pCity.getMaxSpecialistCount(iSpecialist) - pCity.getSpecialistCount(iSpecialist))


def _fallbackSpecialistTargets(pCity, aiFlagged, iDefaultSpecialist):
	'Visible, non-blocked specialist types, candidates to redirect overflow Citizens into.'
	# Reverse XML order: specialist row i sits at y = yResolution - 272 - (26*i) in
	# CvMainInterface, so higher indices draw higher up the screen. Walking from the
	# highest index down matches "top of the panel first" the way the UI reads.
	for i in range(gc.getNumSpecialistInfos() - 1, -1, -1):
		if i == iDefaultSpecialist or i in aiFlagged:
			continue
		if gc.getSpecialistInfo(i).isVisible():
			yield i


def enforceCity(pCity):
	aiFlagged = getAutoRemoveList(pCity)
	if not aiFlagged:
		return

	iDefaultSpecialist = gc.getDefineINT("DEFAULT_SPECIALIST")

	# Any other specialist type always converts straight to DEFAULT_SPECIALIST
	# (plain "Citizen") when removed - that part of CvCity::alterSpecialistCount
	# is unconditional, no AI choice involved, so this half is always safe.
	for iSpecialist in aiFlagged:
		if iSpecialist == iDefaultSpecialist:
			continue
		iCount = pCity.getSpecialistCount(iSpecialist)
		if iCount > 0:
			pCity.alterSpecialistCount(iSpecialist, -iCount)

	if iDefaultSpecialist == -1 or iDefaultSpecialist not in aiFlagged:
		return

	# Citizen is ALSO blocked: the overflow dumped there in the step above (or already
	# sitting there from a previous turn) has to go somewhere else. Increasing a
	# *different* specialist type makes the engine's own AI_removeWorstCitizen() pull
	# the body it needs straight out of the Citizen pool first - before it ever looks
	# at a worked tile - so this reliably moves people out of Citizen into a type we
	# pick ourselves, instead of leaving the engine to choose (and possibly bounce them
	# straight back onto whatever we just blocked).
	for iTarget in _fallbackSpecialistTargets(pCity, aiFlagged, iDefaultSpecialist):
		iResidual = pCity.getSpecialistCount(iDefaultSpecialist)
		if iResidual <= 0:
			break
		iRoom = _specialistRoom(pCity, iTarget)
		if iRoom > 0:
			pCity.alterSpecialistCount(iTarget, min(iRoom, iResidual))

	# Nowhere left with room for a specialist? Last resort: put them to work on an
	# actual tile instead, if the city has one free - alterWorkingPlot() drains the
	# Citizen pool through that same AI_removeWorstCitizen() mechanism.
	iResidual = pCity.getSpecialistCount(iDefaultSpecialist)
	if iResidual > 0:
		for i in range(CITY_HOME_PLOT + 1, NUM_CITY_PLOTS):
			if pCity.getSpecialistCount(iDefaultSpecialist) <= 0:
				break
			if not pCity.isWorkingPlotByIndex(i):
				pPlot = pCity.getCityIndexPlot(i)
				if pPlot and pCity.canWork(pPlot):
					pCity.alterWorkingPlot(i)


def enforcePlayer(iPlayer):
	'Call this once per player turn (onEndPlayerTurn) - never from a UI click.'
	pPlayer = gc.getPlayer(iPlayer)

	(pCity, iter) = pPlayer.firstCity(false)
	while pCity:
		enforceCity(pCity)
		(pCity, iter) = pPlayer.nextCity(iter, false)
