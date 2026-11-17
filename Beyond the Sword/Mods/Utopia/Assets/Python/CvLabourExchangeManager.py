## Utopia
## Labour Exchange: BUILDING_LABOUR_EXCHANGE turns idle workers and specialists
## present in the city into production, every turn.
##
## Disabled entirely (bonus forced to 0) while the city is building a World
## Wonder, a Project (Manhattan, Apollo, spaceship parts, ...), or converting
## production into commerce via a Process (gold/culture/research/espionage) -
## setBuildingYieldChange() is still called with 0 so a leftover bonus from a
## previous turn gets cleared rather than left stuck.
##
## Otherwise the bonus is the sum of two independent parts:
##  - specialists: +1 production for every default (unspecialized) citizen
##    and every Engineer specialist working in the city. This lets the
##    building do something even with no worker units around.
##  - workers: every worker-type unit (any owner, ownership is irrelevant)
##    standing on the city's own plot has a fixed weight - regular Worker 2,
##    Indian Fast Worker 2.5, Robo-Worker 3 - deliberately NOT the unit's
##    real movement points, so the curve below can be tuned independently of
##    unit stats. Only the 3 highest-weight workers present count at full
##    weight; every worker beyond that is multiplied by EXTRA_WORKER_DECAY
##    raised to its position past the third (4th *0.5, 5th *0.25, ...), so
##    piling up workers can't push the bonus past a bounded ceiling.
##
## Driven from CvEventManager.onBeginPlayerTurn. city.setBuildingYieldChange()
## is an absolute set, not a cumulative change (unlike changeExtraYield), so
## simply recomputing it every turn is enough - no delta tracking needed.

from CvPythonExtensions import *

gc = CyGlobalContext()

FULL_WEIGHT_WORKER_COUNT = 3
EXTRA_WORKER_DECAY = 0.5


def isBonusBlocked(pCity):
	'True while the city is building a World Wonder, a Project, or running a production-to-commerce Process.'
	if pCity.isProductionProcess():
		return true

	if pCity.isProductionProject():
		return true

	if pCity.isProductionBuilding() and isWorldWonderClass(gc.getBuildingInfo(pCity.getProductionBuilding()).getBuildingClassType()):
		return true

	return false


def getWorkerProduction(pCity):
	'Weighted, diminishing-returns production from worker-type units (any owner) standing on the city plot.'
	WORKER_WEIGHTS = {
		gc.getInfoTypeForString("UNIT_WORKER"): 2.0,
		gc.getInfoTypeForString("UNIT_INDIAN_FAST_WORKER"): 2.5,
		gc.getInfoTypeForString("UNIT_ROBOWORKER"): 3.0,
	}

	pPlot = pCity.plot()
	aWeights = []
	for i in range(pPlot.getNumUnits()):
		pUnit = pPlot.getUnit(i)
		fWeight = WORKER_WEIGHTS.get(pUnit.getUnitType())
		if fWeight is not None:
			aWeights.append(fWeight)
	aWeights.sort(reverse = true)

	fTotal = 0.0
	for i in range(len(aWeights)):
		fWeight = aWeights[i]
		if i < FULL_WEIGHT_WORKER_COUNT:
			fTotal += fWeight
		else:
			fTotal += fWeight * (EXTRA_WORKER_DECAY ** (i - FULL_WEIGHT_WORKER_COUNT + 1))
	return fTotal


def getSpecialistProduction(pCity):
	'+1 production for every default (unspecialized) citizen and every Engineer specialist in the city.'
	iDefaultSpecialist = gc.getDefineINT("DEFAULT_SPECIALIST")
	iEngineerSpecialist = gc.getInfoTypeForString("SPECIALIST_ENGINEER")

	iCount = 0
	if iDefaultSpecialist != -1:
		iCount += pCity.getSpecialistCount(iDefaultSpecialist)
	if iEngineerSpecialist != -1:
		iCount += pCity.getSpecialistCount(iEngineerSpecialist)
	return iCount


def enforceCity(pCity):
	eBuilding = gc.getInfoTypeForString("BUILDING_LABOUR_EXCHANGE")
	if not pCity.isHasBuilding(eBuilding):
		return

	eBuildingClass = gc.getInfoTypeForString("BUILDINGCLASS_LABOUR_EXCHANGE")

	if isBonusBlocked(pCity):
		pCity.setBuildingYieldChange(eBuildingClass, YieldTypes.YIELD_PRODUCTION, 0)
		return

	iProduction = int(round(getWorkerProduction(pCity) + getSpecialistProduction(pCity)))
	pCity.setBuildingYieldChange(eBuildingClass, YieldTypes.YIELD_PRODUCTION, iProduction)


def enforcePlayer(iPlayer):
	'Call this once per player turn (onBeginPlayerTurn).'
	pPlayer = gc.getPlayer(iPlayer)

	(pCity, iter) = pPlayer.firstCity(false)
	while pCity:
		enforceCity(pCity)
		(pCity, iter) = pPlayer.nextCity(iter, false)
