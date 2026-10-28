## Utopia
## Auto-reinforcement: a standing, per-unit-type "desired count" the player sets once, plus
## a set of cities marked eligible to build towards it. Every end of turn, for each desired
## unit type that's short of its target - counting every copy the player owns anywhere PLUS
## every copy already queued in ANY city, not just the eligible ones - this queues just
## enough new ORDER_TRAIN orders, spread across the eligible cities so they finish as close
## to simultaneously as the engine's own turns-left estimate allows, to close the gap.
## Orders are always appended to the end of a city's queue (same as shift+click on the
## native city screen), never interrupting whatever it's already building.
##
## Same architecture as CvAutoScienceManager/CvAutoGrowthManager - read CvAutoGrowthManager's
## header for the full reasoning:
##  - settings live in CyPlayer.ScriptData (per-player, saved/synced with the player) - always
##    read-modify-write, since CvAutoScienceManager already keeps its own key in that same dict
##  - toggling goes through CyMessageControl().sendModNetMessage() /
##    CvEventManager.onModNetMessage(), never written directly from a click
##  - the actual order-queueing runs from onEndPlayerTurn, which the engine already runs
##    identically on every client
##
## sendPushOrder() (and sendDoTask()) only ever act on the local active player's own city -
## see CvMessageControl::sendPushOrder in the DLL, which hardcodes GC.getGame().getActivePlayer()
## as the order's owner regardless of what player ID is passed to the Cy wrapper - so
## enforcePlayer() is a no-op for every player except whichever one is actually active on
## this client.

from CvPythonExtensions import *
import cPickle as pickle

gc = CyGlobalContext()

# Bumped every time a toggle/count message actually lands (handleToggleCityMessage /
# handleSetDesiredCountMessage). The screen polls this from its own update(fDelta) instead
# of refreshing its lists immediately after sending a message - sendModNetMessage's net
# message only takes effect once CvEventManager.onModNetMessage replays it, which is not
# guaranteed to have happened yet by the time the click handler that sent it returns. A
# synchronous refresh right after sending was reading the state from BEFORE the message
# landed - showing the previous click's result (or none at all) instead of this one's,
# which is what made city/unit rows look one click behind, or stuck, once toggled.
g_iVersion = 0


def _bumpVersion():
	global g_iVersion
	g_iVersion += 1


def getVersion():
	return g_iVersion


SCRIPT_DATA_KEY_SELECTED_CITIES = "AutoMilitarySelectedCities"
SCRIPT_DATA_KEY_DESIRED_COUNTS = "AutoMilitaryDesiredCounts"

MOD_MESSAGE_TOGGLE_CITY = 7264		# tag for CyMessageControl().sendModNetMessage / onModNetMessage
MOD_MESSAGE_SET_DESIRED_COUNT = 7265	# tag for CyMessageControl().sendModNetMessage / onModNetMessage


def _loadPlayerData(pPlayer):
	szData = pPlayer.getScriptData()
	if not szData:
		return {}
	try:
		data = pickle.loads(szData)
	except Exception:
		return {}
	if not isinstance(data, dict):
		return {}
	return data


def _savePlayerData(pPlayer, data):
	pPlayer.setScriptData(pickle.dumps(data))


def getSelectedCityIDs(pPlayer):
	return set(_loadPlayerData(pPlayer).get(SCRIPT_DATA_KEY_SELECTED_CITIES, set()))


def isCitySelected(pCity):
	return pCity.getID() in getSelectedCityIDs(gc.getPlayer(pCity.getOwner()))


def requestToggleCity(pCity):
	'Call this from UI click handlers.'
	bNewValue = not isCitySelected(pCity)
	CyMessageControl().sendModNetMessage(MOD_MESSAGE_TOGGLE_CITY, pCity.getOwner(), pCity.getID(), int(bNewValue), 0)


def requestSetCitiesSelected(pPlayer, cityIDs, bSelected):
	'Call this from "select all" / "reset all" / "top N%" click handlers - one message per city, same as a manual toggle would send.'
	for iCityID in cityIDs:
		CyMessageControl().sendModNetMessage(MOD_MESSAGE_TOGGLE_CITY, pPlayer.getID(), iCityID, int(bSelected), 0)


def handleToggleCityMessage(iData2, iData3, iData4, iData5):
	'Called from CvEventManager.onModNetMessage on every client once the toggle message is replayed.'
	pPlayer = gc.getPlayer(iData2)
	data = _loadPlayerData(pPlayer)
	selected = set(data.get(SCRIPT_DATA_KEY_SELECTED_CITIES, set()))
	if iData4:
		selected.add(iData3)
	else:
		selected.discard(iData3)
	data[SCRIPT_DATA_KEY_SELECTED_CITIES] = selected
	_savePlayerData(pPlayer, data)
	CyInterface().setDirty(InterfaceDirtyBits.CityScreen_DIRTY_BIT, True)
	_bumpVersion()


def getDesiredCounts(pPlayer):
	return dict(_loadPlayerData(pPlayer).get(SCRIPT_DATA_KEY_DESIRED_COUNTS, {}))


def getDesiredCount(pPlayer, eUnit):
	return getDesiredCounts(pPlayer).get(eUnit, 0)


def requestSetDesiredCount(pPlayer, eUnit, iCount):
	'Call this from the stepper +/- click handlers.'
	CyMessageControl().sendModNetMessage(MOD_MESSAGE_SET_DESIRED_COUNT, pPlayer.getID(), eUnit, max(0, iCount), 0)


def handleSetDesiredCountMessage(iData2, iData3, iData4, iData5):
	'Called from CvEventManager.onModNetMessage on every client once the count message is replayed.'
	pPlayer = gc.getPlayer(iData2)
	data = _loadPlayerData(pPlayer)
	counts = dict(data.get(SCRIPT_DATA_KEY_DESIRED_COUNTS, {}))
	if iData4 <= 0:
		counts.pop(iData3, None)
	else:
		counts[iData3] = iData4
	data[SCRIPT_DATA_KEY_DESIRED_COUNTS] = counts
	_savePlayerData(pPlayer, data)
	CyInterface().setDirty(InterfaceDirtyBits.CityScreen_DIRTY_BIT, True)
	_bumpVersion()


def countUnitTypeEverywhere(pPlayer, eUnit):
	'Every living copy the player owns, anywhere, plus every copy already queued (built or not) in any of the players cities - not just the ones eligible for auto-assignment.'
	iCount = 0

	(pUnit, iter) = pPlayer.firstUnit(false)
	while pUnit:
		if pUnit.getUnitType() == eUnit:
			iCount += 1
		(pUnit, iter) = pPlayer.nextUnit(iter, false)

	(pCity, iter) = pPlayer.firstCity(false)
	while pCity:
		for i in range(pCity.getOrderQueueLength()):
			order = pCity.getOrderFromQueue(i)
			if (order.eOrderType == OrderTypes.ORDER_TRAIN) and (order.iData1 == eUnit):
				iCount += 1
		(pCity, iter) = pPlayer.nextCity(iter, false)

	return iCount


def enforcePlayer(iPlayer):
	'Call this once per player turn (onEndPlayerTurn) - never from a UI click.'
	if iPlayer != gc.getGame().getActivePlayer():
		return

	pPlayer = gc.getPlayer(iPlayer)
	if not pPlayer.isAlive():
		return

	desiredCounts = getDesiredCounts(pPlayer)
	if not desiredCounts:
		return

	selectedCityIDs = getSelectedCityIDs(pPlayer)
	if not selectedCityIDs:
		return

	eligibleCities = []
	(pCity, iter) = pPlayer.firstCity(false)
	while pCity:
		if pCity.getID() in selectedCityIDs:
			eligibleCities.append(pCity)
		(pCity, iter) = pPlayer.nextCity(iter, false)

	if not eligibleCities:
		return

	for eUnit, iDesired in desiredCounts.items():
		if iDesired <= 0:
			continue

		iShort = iDesired - countUnitTypeEverywhere(pPlayer, eUnit)
		if iShort <= 0:
			continue

		candidates = [pCity for pCity in eligibleCities if pCity.canTrain(eUnit, False, False)]
		if not candidates:
			continue

		# getUnitProductionNeeded is a CyPlayer method, not a CyCity one - cost doesn't vary
		# per city here, same as how CvConstructionPlanner's own unit list prices things.
		iUnitCost = pPlayer.getUnitProductionNeeded(eUnit)

		# Picks the city with the lowest turns-equivalent tentatively piled onto it SO FAR in
		# this loop, weighted by its own hammer rate - a city twice as productive ends up
		# with roughly twice as many of the new orders. This is computed entirely ourselves
		# rather than via getUnitProductionTurnsLeft(eUnit, iHypotheticalQueuePos): that call
		# only reflects the city's REAL current queue, which sendPushOrder below has not
		# actually landed in yet (it is a networked message, same as the toggle/count ones
		# this module also sends) - every pick within one single pass was reading the exact
		# same real state and so always favored whichever city happened to be first in the
		# candidates list, instead of spreading across them.
		eligibleLoad = {}
		for pCity in candidates:
			eligibleLoad[pCity.getID()] = pCity.getOrderQueueLength() * iUnitCost

		for i in range(iShort):
			bestCity = None
			bestEta = None
			for pCity in candidates:
				iRate = pCity.getYieldRate(YieldTypes.YIELD_PRODUCTION)
				if (iRate <= 0):
					continue
				iEta = eligibleLoad[pCity.getID()] / float(iRate)
				if (bestCity is None) or (iEta < bestEta):
					bestCity = pCity
					bestEta = iEta

			if (bestCity is None):
				break

			CyMessageControl().sendPushOrder(bestCity.getID(), OrderTypes.ORDER_TRAIN, eUnit, False, True, False)
			eligibleLoad[bestCity.getID()] += iUnitCost
