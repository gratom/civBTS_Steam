## Utopia
## Labour Exchange: BUILDING_LABOUR_EXCHANGE converts idle worker-type units
## standing on the city's own plot into production, every turn.
##
## Ownership of the worker units is irrelevant (an ally's worker sitting on
## your city tile counts too) - only unit class and presence on the plot
## matter. The bonus per unit equals that unit's movement points for the
## turn (regular Worker 2, Indian Fast Worker 3, Robo-Worker 4) - the first
## two share UNITCLASS_WORKER regardless of civ, so no per-civ handling is
## needed.
##
## Driven from CvEventManager.onBeginPlayerTurn. city.setBuildingYieldChange()
## is an absolute set, not a cumulative change (unlike changeExtraYield), so
## simply recomputing it every turn is enough - no delta tracking needed.

from CvPythonExtensions import *

gc = CyGlobalContext()


def getWorkerProduction(pCity):
	'Sum of the movement points of every worker-type unit (any owner) standing on the city plot.'
	iWorkerClass = gc.getInfoTypeForString("UNITCLASS_WORKER")
	iRoboWorkerClass = gc.getInfoTypeForString("UNITCLASS_ROBOWORKER")

	pPlot = pCity.plot()
	iTotal = 0
	for i in range(pPlot.getNumUnits()):
		pUnit = pPlot.getUnit(i)
		eUnitClass = pUnit.getUnitClassType()
		if eUnitClass == iWorkerClass or eUnitClass == iRoboWorkerClass:
			iTotal += pUnit.baseMoves()
	return iTotal


def enforceCity(pCity):
	eBuilding = gc.getInfoTypeForString("BUILDING_LABOUR_EXCHANGE")
	if not pCity.isHasBuilding(eBuilding):
		return

	eBuildingClass = gc.getInfoTypeForString("BUILDINGCLASS_LABOUR_EXCHANGE")
	pCity.setBuildingYieldChange(eBuildingClass, YieldTypes.YIELD_PRODUCTION, getWorkerProduction(pCity))


def enforcePlayer(iPlayer):
	'Call this once per player turn (onBeginPlayerTurn).'
	pPlayer = gc.getPlayer(iPlayer)

	(pCity, iter) = pPlayer.firstCity(false)
	while pCity:
		enforceCity(pCity)
		(pCity, iter) = pPlayer.nextCity(iter, false)
