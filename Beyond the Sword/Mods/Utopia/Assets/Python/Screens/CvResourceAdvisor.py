## Utopia mod - Resource Advisor
## Shows, per improvement type (mine, quarry, farm, etc. - driven entirely off
## CIV4ImprovementInfos.xml, not a hardcoded list), how many of that improvement the player
## has, how many already carry a resource, how many don't, how many of those are actually
## being worked this turn (only worked plots are even eligible for the discovery roll), and
## for every resource that improvement could still reveal, the exact expected number of NEW
## discoveries across all eligible plots over the next 1 / 10 / 100 turns.
##
## Discovery mechanics (CvPlot::doImprovement in the DLL): once a turn, for every WORKED plot
## whose improvement doesn't have a resource yet, the game walks every bonus type in bonus-
## index order; for each one the owning team already has the reveal tech for and whose
## iDiscoverRand (CIV4ImprovementInfos.xml BonusTypeStructs) is > 0, it rolls 1-in-iDiscoverRand
## and, on the first roll that hits, assigns that resource and stops - so later bonus types in
## the list are never even rolled that turn if an earlier one already succeeded. That means the
## real per-turn chance of resource j specifically appearing is
##   P_turn(j) = p_j * PRODUCT_{i before j in the list} (1 - p_i),   p_i = 1 / iDiscoverRand_i
## and the chance ANY resource appears that turn is P_any = 1 - PRODUCT_i (1 - p_i). Over N
## turns (while nothing has been found yet) that is a geometric race between outcomes:
##   P(j found within N turns) = [1 - (1-P_any)^N] * (P_turn(j) / P_any)
## and the expected COUNT of plots finding resource j within N turns, across M identically-
## eligible plots, is simply M times that single-plot probability - expectation is linear in
## the plot count, no matter how many mines/quarries/farms are involved.
##
## The extra "~N turns" column is the mean of a geometric distribution: across M eligible
## plots, the chance SOME plot hits resource j in a given turn is q = 1-(1-P_turn(j))^M, so
## the expected number of turns until the first hit anywhere is 1/q.
from CvPythonExtensions import *
import CvUtil
import CvScreenEnums

gc = CyGlobalContext()
localText = CyTranslator()

SCREEN_NAME = "ResourceAdvisor"
PANEL_NAME = "ResourceAdvisorScroll"

TURN_HORIZONS = (1, 10, 100)

ROW_HEIGHT = 30
ICON_SIZE = 26
NAME_WIDTH = 190
COUNT_WIDTH = 46
CHANCE_WIDTH = 78
COLUMN_GAP = 6

X_ICON = 0
X_NAME = X_ICON + ICON_SIZE + COLUMN_GAP
X_TOTAL = X_NAME + NAME_WIDTH + COLUMN_GAP
X_WITH = X_TOTAL + COUNT_WIDTH + COLUMN_GAP
X_WITHOUT = X_WITH + COUNT_WIDTH + COLUMN_GAP
X_WORKED = X_WITHOUT + COUNT_WIDTH + COLUMN_GAP
X_T1 = X_WORKED + COUNT_WIDTH + COLUMN_GAP
X_T10 = X_T1 + CHANCE_WIDTH + COLUMN_GAP
X_T100 = X_T10 + CHANCE_WIDTH + COLUMN_GAP
X_EXPECTED_TURNS = X_T100 + CHANCE_WIDTH + COLUMN_GAP
PANEL_CONTENT_WIDTH = X_EXPECTED_TURNS + CHANCE_WIDTH

class CvResourceAdvisor:
	"Resource Advisor Screen - odds of discovering a hidden resource on worked improvements"
	def __init__(self):
		self.discoveryCandidatesByImprovement = None
		self.rowWidgetCount = 0

	# Static, player-independent: {eImprovement: [(eBonus, iDiscoverRand), ...]} in bonus-index
	# order (the same order CvPlot::doImprovement checks them in - that order is what the math
	# in the module header is built around). Cached once since this is pure game-rule data.
	def getDiscoveryCandidates(self):
		if self.discoveryCandidatesByImprovement is None:
			self.discoveryCandidatesByImprovement = {}
			for eImprovement in range(gc.getNumImprovementInfos()):
				improvementInfo = gc.getImprovementInfo(eImprovement)
				candidates = []
				for eBonus in range(gc.getNumBonusInfos()):
					iDiscoverRand = improvementInfo.getImprovementBonusDiscoverRand(eBonus)
					if iDiscoverRand > 0:
						candidates.append((eBonus, iDiscoverRand))
				if candidates:
					self.discoveryCandidatesByImprovement[eImprovement] = candidates
		return self.discoveryCandidatesByImprovement

	# Counts every plot the given player owns, grouped by improvement type: total / already
	# has a resource / doesn't / doesn't AND is actually being worked this turn by a city that
	# isn't in disorder - that last count is the only one the discovery roll actually applies
	# to, since CvCity::doTurn only calls doImprovement() on plots it is currently working.
	def countImprovementPlots(self, ePlayer):
		counts = {}
		pMap = CyMap()
		for i in range(pMap.numPlots()):
			pPlot = pMap.plotByIndex(i)
			if pPlot.getOwner() != ePlayer:
				continue
			eImprovement = pPlot.getImprovementType()
			if eImprovement == -1:
				continue

			d = counts.get(eImprovement)
			if d is None:
				d = {"total": 0, "withBonus": 0, "withoutBonus": 0, "worked": 0}
				counts[eImprovement] = d

			d["total"] += 1
			if pPlot.getBonusType(-1) != -1:
				d["withBonus"] += 1
			else:
				d["withoutBonus"] += 1
				pWorkingCity = pPlot.getWorkingCity()
				if pPlot.isBeingWorked() and pWorkingCity and not pWorkingCity.isDisorder():
					d["worked"] += 1
		return counts

	# Per-turn discovery probabilities for one improvement, given which reveal techs the
	# player's team currently has - see the module header for the exact formulas. Returns
	# (perBonusChance, pAny): perBonusChance is [(eBonus, P_turn_specific), ...] in bonus-index
	# order (skipping bonuses whose reveal tech isn't known yet), pAny is the combined
	# "something gets found this turn" probability.
	def computeTurnProbabilities(self, candidates, iTeam):
		pTeam = gc.getTeam(iTeam)
		perBonusChance = []
		qProduct = 1.0
		for (eBonus, iDiscoverRand) in candidates:
			eTechReveal = gc.getBonusInfo(eBonus).getTechReveal()
			if eTechReveal != -1 and not pTeam.isHasTech(eTechReveal):
				continue
			p = 1.0 / iDiscoverRand
			perBonusChance.append((eBonus, p * qProduct))
			qProduct *= (1.0 - p)
		pAny = 1.0 - qProduct
		return (perBonusChance, pAny)

	# Expected number of plots (out of nWorked) that will have landed on THIS SPECIFIC outcome
	# (pThis per turn) within N turns, correctly accounting for the fact that a plot stops
	# rolling entirely the moment it finds *any* resource (pAny per turn) - see module header.
	def expectedCount(self, nWorked, pThis, pAny, N):
		if nWorked <= 0 or pAny <= 0:
			return 0.0
		pFoundByN = 1.0 - ((1.0 - pAny) ** N)
		return nWorked * pFoundByN * (pThis / pAny)

	# Approximately how many turns until the FIRST of the nWorked eligible plots lands on
	# this outcome (pThis per turn, per plot) - the mean of a geometric distribution. Treats
	# nWorked as constant, which is a fine approximation here: these per-turn odds are tiny
	# (1/iDiscoverRand, typically in the thousands), so across the handful of turns where a
	# first hit actually becomes likely, "how many eligible plots are left" barely moves.
	#   q = chance SOME plot (out of nWorked) hits this turn = 1 - (1-pThis)^nWorked
	#   E[turns until first hit] = 1 / q
	def expectedTurnsUntilFirst(self, nWorked, pThis):
		if nWorked <= 0 or pThis <= 0:
			return None
		q = 1.0 - ((1.0 - pThis) ** nWorked)
		if q <= 0.0:
			return None
		return 1.0 / q

	# One row entry per improvement that both has at least one plot and at least one
	# currently-knowable (reveal tech already researched) resource left to find.
	# Each entry: (eImprovement, countsDict, anyExpected[3], anyExpectedTurns, resourceRows)
	# where resourceRows is [(eBonus, expected[3], expectedTurns), ...] and anyExpected/
	# expected are keyed to TURN_HORIZONS.
	def computeRows(self):
		ePlayer = gc.getGame().getActivePlayer()
		iTeam = gc.getPlayer(ePlayer).getTeam()
		counts = self.countImprovementPlots(ePlayer)
		candidatesByImprovement = self.getDiscoveryCandidates()

		rows = []
		for eImprovement in range(gc.getNumImprovementInfos()):
			countsForImprovement = counts.get(eImprovement)
			if not countsForImprovement or countsForImprovement["total"] == 0:
				continue
			candidates = candidatesByImprovement.get(eImprovement)
			if not candidates:
				continue

			(perBonusChance, pAny) = self.computeTurnProbabilities(candidates, iTeam)
			if not perBonusChance:
				continue

			nWorked = countsForImprovement["worked"]
			anyExpected = [self.expectedCount(nWorked, pAny, pAny, N) for N in TURN_HORIZONS]
			anyExpectedTurns = self.expectedTurnsUntilFirst(nWorked, pAny)

			resourceRows = []
			for (eBonus, pThis) in perBonusChance:
				expected = [self.expectedCount(nWorked, pThis, pAny, N) for N in TURN_HORIZONS]
				expectedTurns = self.expectedTurnsUntilFirst(nWorked, pThis)
				resourceRows.append((eBonus, expected, expectedTurns))

			rows.append((eImprovement, countsForImprovement, anyExpected, anyExpectedTurns, resourceRows))

		return rows

	# Shown as a percentage - fValue is an expected COUNT (can exceed 1 when there are many
	# eligible plots over a long horizon), so this can read above 100%, which is correct: it
	# just means "on average more than one" rather than a bounded single-event probability.
	def formatExpected(self, fValue):
		return u"%.2f%%" % (fValue * 100.0)

	# "~N" turns until the first of the eligible plots is expected to hit - None means no
	# eligible plots (or a zero chance), shown as a dash rather than a bogus number.
	def formatExpectedTurns(self, fValue):
		if fValue is None:
			return u"-"
		return u"~" + unicode(int(round(fValue)))

	# Screen construction function
	def interfaceScreen(self):
		screen = CyGInterfaceScreen( SCREEN_NAME, CvScreenEnums.RESOURCE_ADVISOR )

		self.nScreenWidth = PANEL_CONTENT_WIDTH + 60
		self.nScreenHeight = 560
		self.nListX = 20
		self.nHeaderY = 55
		self.nListY = self.nHeaderY + 26
		self.nListHeight = self.nScreenHeight - self.nListY - 50

		screen.setRenderInterfaceOnly(True)
		screen.setDimensions(100, 80, self.nScreenWidth, self.nScreenHeight)
		screen.showScreen(PopupStates.POPUPSTATE_IMMEDIATE, False)

		screen.addPanel( "ResourceAdvisorBG", u"", u"", True, False, 0, 0, self.nScreenWidth, self.nScreenHeight, PanelStyles.PANEL_STYLE_MAIN )

		screen.setLabel( "ResourceAdvisorTitle", "Background", localText.getText("TXT_KEY_UTOPIA_RESOURCE_ADVISOR", ()), CvUtil.FONT_LEFT_JUSTIFY, self.nListX, 20, -0.1, FontTypes.TITLE_FONT, WidgetTypes.WIDGET_GENERAL, -1, -1 )

		self.drawColumnHeaders(screen)

		rows = self.computeRows()

		self.rowWidgetCount = 0
		for (eImprovement, countsForImprovement, anyExpected, anyExpectedTurns, resourceRows) in rows:
			self.rowWidgetCount += 1 + len(resourceRows)

		screen.addScrollPanel( PANEL_NAME, u"", self.nListX, self.nListY, PANEL_CONTENT_WIDTH, self.nListHeight, PanelStyles.PANEL_STYLE_EXTERNAL )
		screen.setViewMin( PANEL_NAME, PANEL_CONTENT_WIDTH, max(self.nListHeight, self.rowWidgetCount * ROW_HEIGHT) )
		screen.show( PANEL_NAME )

		self.drawRows(screen, rows)

		# Close button, bottom right - same style as the other advisor screens
		screen.setText( "ResourceAdvisorClose", "Background", localText.getText("TXT_KEY_PEDIA_SCREEN_EXIT", ()).upper(), CvUtil.FONT_RIGHT_JUSTIFY, self.nScreenWidth - 25, self.nScreenHeight - 35, -0.1, FontTypes.TITLE_FONT, WidgetTypes.WIDGET_CLOSE_SCREEN, -1, -1 )

	def drawColumnHeaders(self, screen):
		y = self.nHeaderY
		screen.setLabel( "ResourceAdvisorHdrName", "Background", localText.getText("TXT_KEY_DOMESTIC_ADVISOR_NAME", ()), CvUtil.FONT_LEFT_JUSTIFY, self.nListX + X_NAME, y, -0.1, FontTypes.SMALL_FONT, WidgetTypes.WIDGET_GENERAL, -1, -1 )
		screen.setLabel( "ResourceAdvisorHdrTotal", "Background", localText.getText("TXT_KEY_UTOPIA_RESOURCE_ADVISOR_TOTAL", ()), CvUtil.FONT_LEFT_JUSTIFY, self.nListX + X_TOTAL, y, -0.1, FontTypes.SMALL_FONT, WidgetTypes.WIDGET_GENERAL, -1, -1 )
		screen.setLabel( "ResourceAdvisorHdrWith", "Background", localText.getText("TXT_KEY_UTOPIA_RESOURCE_ADVISOR_WITH_BONUS", ()), CvUtil.FONT_LEFT_JUSTIFY, self.nListX + X_WITH, y, -0.1, FontTypes.SMALL_FONT, WidgetTypes.WIDGET_GENERAL, -1, -1 )
		screen.setLabel( "ResourceAdvisorHdrWithout", "Background", localText.getText("TXT_KEY_UTOPIA_RESOURCE_ADVISOR_WITHOUT_BONUS", ()), CvUtil.FONT_LEFT_JUSTIFY, self.nListX + X_WITHOUT, y, -0.1, FontTypes.SMALL_FONT, WidgetTypes.WIDGET_GENERAL, -1, -1 )
		screen.setLabel( "ResourceAdvisorHdrWorked", "Background", localText.getText("TXT_KEY_UTOPIA_RESOURCE_ADVISOR_WORKED", ()), CvUtil.FONT_LEFT_JUSTIFY, self.nListX + X_WORKED, y, -0.1, FontTypes.SMALL_FONT, WidgetTypes.WIDGET_GENERAL, -1, -1 )
		screen.setLabel( "ResourceAdvisorHdrT1", "Background", localText.getText("TXT_KEY_UTOPIA_RESOURCE_ADVISOR_1_TURN", ()), CvUtil.FONT_LEFT_JUSTIFY, self.nListX + X_T1, y, -0.1, FontTypes.SMALL_FONT, WidgetTypes.WIDGET_GENERAL, -1, -1 )
		screen.setLabel( "ResourceAdvisorHdrT10", "Background", localText.getText("TXT_KEY_UTOPIA_RESOURCE_ADVISOR_10_TURNS", ()), CvUtil.FONT_LEFT_JUSTIFY, self.nListX + X_T10, y, -0.1, FontTypes.SMALL_FONT, WidgetTypes.WIDGET_GENERAL, -1, -1 )
		screen.setLabel( "ResourceAdvisorHdrT100", "Background", localText.getText("TXT_KEY_UTOPIA_RESOURCE_ADVISOR_100_TURNS", ()), CvUtil.FONT_LEFT_JUSTIFY, self.nListX + X_T100, y, -0.1, FontTypes.SMALL_FONT, WidgetTypes.WIDGET_GENERAL, -1, -1 )
		screen.setLabel( "ResourceAdvisorHdrExpectedTurns", "Background", localText.getText("TXT_KEY_UTOPIA_RESOURCE_ADVISOR_EXPECTED_TURNS", ()), CvUtil.FONT_LEFT_JUSTIFY, self.nListX + X_EXPECTED_TURNS, y, -0.1, FontTypes.SMALL_FONT, WidgetTypes.WIDGET_GENERAL, -1, -1 )

	# Draws every row once, all at once, inside the scroll panel's content space (coordinates
	# here are relative to the panel's content, not the screen - same approach as the
	# Construction Planner's building/unit lists).
	def drawRows(self, screen, rows):
		iRow = 0
		for (eImprovement, countsForImprovement, anyExpected, anyExpectedTurns, resourceRows) in rows:
			self.drawImprovementRow(screen, iRow, eImprovement, countsForImprovement, anyExpected, anyExpectedTurns)
			iRow += 1
			for (eBonus, expected, expectedTurns) in resourceRows:
				self.drawResourceRow(screen, iRow, eBonus, expected, expectedTurns)
				iRow += 1

	def drawImprovementRow(self, screen, iRow, eImprovement, countsForImprovement, anyExpected, anyExpectedTurns):
		y = iRow * ROW_HEIGHT
		improvementInfo = gc.getImprovementInfo(eImprovement)

		screen.addDDSGFCAt( "ResourceAdvisorIcon" + str(iRow), PANEL_NAME, improvementInfo.getButton(), X_ICON, y, ICON_SIZE, ICON_SIZE, WidgetTypes.WIDGET_GENERAL, -1, -1, False )

		szName = u"<font=2b>" + improvementInfo.getDescription() + u"</font>"
		screen.setTextAt( "ResourceAdvisorName" + str(iRow), PANEL_NAME, szName, CvUtil.FONT_LEFT_JUSTIFY, X_NAME, y + 4, -0.1, FontTypes.SMALL_FONT, WidgetTypes.WIDGET_GENERAL, -1, -1 )
		screen.show( "ResourceAdvisorName" + str(iRow) )

		self.setCountLabel( screen, "ResourceAdvisorTotal" + str(iRow), X_TOTAL, y, unicode(countsForImprovement["total"]) )
		self.setCountLabel( screen, "ResourceAdvisorWith" + str(iRow), X_WITH, y, unicode(countsForImprovement["withBonus"]) )
		self.setCountLabel( screen, "ResourceAdvisorWithout" + str(iRow), X_WITHOUT, y, unicode(countsForImprovement["withoutBonus"]) )
		self.setCountLabel( screen, "ResourceAdvisorWorked" + str(iRow), X_WORKED, y, unicode(countsForImprovement["worked"]) )

		self.setCountLabel( screen, "ResourceAdvisorT1_" + str(iRow), X_T1, y, self.formatExpected(anyExpected[0]) )
		self.setCountLabel( screen, "ResourceAdvisorT10_" + str(iRow), X_T10, y, self.formatExpected(anyExpected[1]) )
		self.setCountLabel( screen, "ResourceAdvisorT100_" + str(iRow), X_T100, y, self.formatExpected(anyExpected[2]) )
		self.setCountLabel( screen, "ResourceAdvisorExpTurns" + str(iRow), X_EXPECTED_TURNS, y, self.formatExpectedTurns(anyExpectedTurns) )

	def drawResourceRow(self, screen, iRow, eBonus, expected, expectedTurns):
		y = iRow * ROW_HEIGHT
		bonusInfo = gc.getBonusInfo(eBonus)

		screen.addDDSGFCAt( "ResourceAdvisorIcon" + str(iRow), PANEL_NAME, bonusInfo.getButton(), X_ICON, y, ICON_SIZE, ICON_SIZE, WidgetTypes.WIDGET_GENERAL, -1, -1, False )

		szName = u"   " + bonusInfo.getDescription()
		screen.setTextAt( "ResourceAdvisorName" + str(iRow), PANEL_NAME, szName, CvUtil.FONT_LEFT_JUSTIFY, X_NAME, y + 4, -0.1, FontTypes.SMALL_FONT, WidgetTypes.WIDGET_GENERAL, -1, -1 )
		screen.show( "ResourceAdvisorName" + str(iRow) )

		self.setCountLabel( screen, "ResourceAdvisorT1_" + str(iRow), X_T1, y, self.formatExpected(expected[0]) )
		self.setCountLabel( screen, "ResourceAdvisorT10_" + str(iRow), X_T10, y, self.formatExpected(expected[1]) )
		self.setCountLabel( screen, "ResourceAdvisorT100_" + str(iRow), X_T100, y, self.formatExpected(expected[2]) )
		self.setCountLabel( screen, "ResourceAdvisorExpTurns" + str(iRow), X_EXPECTED_TURNS, y, self.formatExpectedTurns(expectedTurns) )

	def setCountLabel(self, screen, szWidgetName, x, y, szText):
		screen.setLabelAt( szWidgetName, PANEL_NAME, szText, CvUtil.FONT_LEFT_JUSTIFY, x, y + 6, -0.1, FontTypes.SMALL_FONT, WidgetTypes.WIDGET_GENERAL, -1, -1 )
		screen.show( szWidgetName )

	# Purely a point-in-time snapshot (counts, techs, working tiles) taken when the screen is
	# opened - nothing here needs a live per-frame refresh, so this is intentionally a no-op.
	def update(self, fDelta):
		return

	def handleInput(self, inputClass):
		return 0
