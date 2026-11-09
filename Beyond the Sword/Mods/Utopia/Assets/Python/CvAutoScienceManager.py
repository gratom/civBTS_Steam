## Utopia
## "Smart science": a per-player switch that automatically slides the research
## percent to the highest value that still keeps gold income non-negative,
## preferring more gold over a marginally higher science percent whenever the
## current research would finish in the same number of turns either way.
##
## Same architecture as CvAutoGrowthManager - read that file's header for the
## full reasoning:
##  - the flag lives in CyPlayer.ScriptData (per-player, saved/synced with the player)
##  - toggling goes through CyMessageControl().sendModNetMessage() /
##    CvEventManager.onModNetMessage(), never written directly from a click
##  - the actual percent search and the CommercePercent change runs from
##    onEndPlayerTurn, which the engine already runs identically on every client
##
## Unlike EMPHASIZE_AVOID_GROWTH, CyPlayer.setCommercePercent() is a directly
## exposed setter, so no sendDoTask() detour is needed here - enforcePlayer()
## calls it straight.

from CvPythonExtensions import *
import cPickle as pickle

gc = CyGlobalContext()

SCRIPT_DATA_KEY = "AutoScience"
MOD_MESSAGE_TOGGLE_AUTO_SCIENCE = 7263	# tag for CyMessageControl().sendModNetMessage / onModNetMessage


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


def isAutoScience(pPlayer):
	return bool(_loadPlayerData(pPlayer).get(SCRIPT_DATA_KEY, False))


def requestToggle(pPlayer):
	'Call this from UI click handlers.'
	bNewValue = not isAutoScience(pPlayer)
	CyMessageControl().sendModNetMessage(MOD_MESSAGE_TOGGLE_AUTO_SCIENCE, pPlayer.getID(), 0, 0, int(bNewValue))


def handleNetMessage(iData2, iData3, iData4, iData5):
	'Called from CvEventManager.onModNetMessage on every client once the toggle message is replayed.'
	pPlayer = gc.getPlayer(iData2)
	data = _loadPlayerData(pPlayer)
	data[SCRIPT_DATA_KEY] = bool(iData5)
	_savePlayerData(pPlayer, data)
	CyInterface().setDirty(InterfaceDirtyBits.PercentButtons_DIRTY_BIT, True)
	CyInterface().setDirty(InterfaceDirtyBits.GameData_DIRTY_BIT, True)


def _turnsToCompleteResearch(pPlayer, eTech):
	'Lower is faster. A tech that cannot be reached at the current rate counts as effectively infinite.'
	pTeam = gc.getTeam(pPlayer.getTeam())
	iProgress = pTeam.getResearchProgress(eTech)
	iOverflow = (pPlayer.getOverflowResearch() * pPlayer.calculateResearchModifier(eTech)) / 100
	iCost = pTeam.getResearchCost(eTech)
	iRate = pPlayer.calculateResearchRate(-1)

	iRemaining = iCost - iProgress - iOverflow
	if iRemaining <= 0:
		return 0
	if iRate <= 0:
		return 0x7FFFFFFF

	return (iRemaining + iRate - 1) / iRate	# ceiling division


def _applyResearchPercent(pPlayer, mapOriginalPercents, iPercent):
	'Sets the research slider to iPercent while keeping the OTHER flexible sliders (gold, espionage) as close to their original relative split as the engine allows.'
	eResearch = CommerceTypes.COMMERCE_RESEARCH
	for eCommerce, iOrigPercent in mapOriginalPercents.items():
		if eCommerce != eResearch and pPlayer.isCommerceFlexible(eCommerce):
			pPlayer.setCommercePercent(eCommerce, iOrigPercent)
	pPlayer.setCommercePercent(eResearch, iPercent)


def enforcePlayer(iPlayer):
	'Call this once per player turn (onBeginPlayerTurn, before doGold()/doResearch() credit the turn) - never from a UI click.'
	pPlayer = gc.getPlayer(iPlayer)

	if not isAutoScience(pPlayer):
		return
	if not pPlayer.isAlive() or pPlayer.isAnarchy():
		return

	eResearch = CommerceTypes.COMMERCE_RESEARCH
	if not pPlayer.isCommerceFlexible(eResearch):
		return

	eTech = pPlayer.getCurrentResearch()
	if eTech == -1:
		# Nothing queued - there is no "turns to complete" to optimize against, leave the slider alone.
		return

	iStep = gc.getDefineINT("COMMERCE_PERCENT_CHANGE_INCREMENTS")
	if iStep <= 0:
		iStep = 10

	mapOriginalPercents = {}
	for iI in range(CommerceTypes.NUM_COMMERCE_TYPES):
		eCommerce = CommerceTypes(iI)
		mapOriginalPercents[eCommerce] = pPlayer.getCommercePercent(eCommerce)

	aPercents = list(range(0, 100, iStep))
	aPercents.append(100)

	# Try every candidate percent and record (actual percent, turns to finish current tech, resulting gold/turn).
	aCandidates = []
	for iPercent in aPercents:
		_applyResearchPercent(pPlayer, mapOriginalPercents, iPercent)
		iActualPercent = pPlayer.getCommercePercent(eResearch)
		iGoldRate = pPlayer.calculateGoldRate()
		iTurns = _turnsToCompleteResearch(pPlayer, eTech)
		aCandidates.append((iActualPercent, iTurns, iGoldRate))

	aAffordable = [c for c in aCandidates if c[2] >= 0]

	if aAffordable:
		# Among the percents that keep gold non-negative, take the ones that finish research
		# in the fewest turns, then - since extra science beyond that point buys nothing - pick
		# whichever of those keeps the most gold (i.e. the lowest percent in that tied group).
		# (min()/max() take no "key" argument on the game's embedded Python 2.4, so sort instead.)
		iMinTurns = min([c[1] for c in aAffordable])
		aFastest = [c for c in aAffordable if c[1] == iMinTurns]
		aFastest.sort(key=lambda c: c[2])
		best = aFastest[-1]
	else:
		# Can't stay gold-positive at any percent - fall back to the percent that costs least gold.
		aByPercent = aCandidates[:]
		aByPercent.sort(key=lambda c: c[0])
		best = aByPercent[0]

	_applyResearchPercent(pPlayer, mapOriginalPercents, best[0])

	if iPlayer == gc.getGame().getActivePlayer():
		CyInterface().setDirty(InterfaceDirtyBits.PercentButtons_DIRTY_BIT, True)
		CyInterface().setDirty(InterfaceDirtyBits.GameData_DIRTY_BIT, True)
