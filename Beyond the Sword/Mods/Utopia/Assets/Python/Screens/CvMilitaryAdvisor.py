## Sid Meier's Civilization 4
## Copyright Firaxis Games 2005
from CvPythonExtensions import *
import CvUtil
import ScreenInput
import time
import PyHelpers
import re
import math

PyPlayer = PyHelpers.PyPlayer
PyInfo = PyHelpers.PyInfo

# globals
gc = CyGlobalContext()
ArtFileMgr = CyArtFileMgr()
localText = CyTranslator()

COLUMN_PRODUCTION_CITY = 0
COLUMN_PRODUCTION_UNIT = 1
COLUMN_PRODUCTION_TURNS = 2

class CvMilitaryAdvisor:
	"Military Advisor"

	def __init__(self, screenId):
		self.screenId = screenId
		self.MILITARY_SCREEN_NAME = "MilitaryAdvisor"
		self.BACKGROUND_ID = "MilitaryAdvisorBackground"
		self.EXIT_ID = "MilitaryAdvisorExitWidget"

		self.WIDGET_ID = "MilitaryAdvisorWidget"
		self.REFRESH_WIDGET_ID = "MilitaryAdvisorRefreshWidget"
		self.ATTACH_WIDGET_ID = "MilitaryAdvisorAttachWidget"
		self.SELECTION_WIDGET_ID = "MilitaryAdvisorSelectionWidget"
		self.ATTACHED_WIDGET_ID = "MilitaryAdvisorAttachedWidget" # no need to explicitly delete these
		self.LEADER_BUTTON_ID = "MilitaryAdvisorLeaderButton"
		self.UNIT_PANEL_ID = "MilitaryAdvisorUnitPanel"
		self.UNIT_BUTTON_ID = "MilitaryAdvisorUnitButton"
		self.UNIT_BUTTON_LABEL_ID = "MilitaryAdvisorUnitButtonLabel"
		self.LEADER_PANEL_ID = "MilitaryAdvisorLeaderPanel"
		self.UNIT_LIST_ID = "MilitaryAdvisorUnitList"
		self.GREAT_GENERAL_BAR_ID = "MilitaryAdvisorGreatGeneralBar"
		self.GREAT_GENERAL_LABEL_ID = "MilitaryAdvisorGreatGeneralLabel"
		self.RALLY_CANVAS_ID = "MilitaryAdvisorRallyCanvas"
		self.RALLY_LINE_ID = "MilitaryAdvisorRallyLine"
		self.nRallyLineCount = 0
		# Extra columns of terrain the minimap duplicates across the whole width because of
		# cylindrical map wrap (observed as roughly 3 tiles combined) - see plotToMinimapXY.
		self.MAP_WRAP_PADDING = 3.0

		self.PRODUCTION_LIST_ID = "MilitaryAdvisorProductionList"
		self.RESERVED_PANEL_ID = "MilitaryAdvisorReservedPanel"

		self.Z_BACKGROUND = -2.1
		self.Z_CONTROLS = self.Z_BACKGROUND - 0.2
		self.DZ = -0.2

		self.Y_TITLE = 8
		self.BORDER_WIDTH = 4
		self.W_HELP_AREA = 200

		self.MAP_MARGIN = 20

		self.nWidgetCount = 0
		self.nRefreshWidgetCount = 0
		self.nAttachedWidgetCount = 0
		self.iActivePlayer = -1
		self.selectedPlayerList = []
		self.selectedGroupList = []
		self.selectedUnitList = []

		self.X_LEADERS = 20
		self.Y_LEADERS = 80
		self.H_LEADERS = 90
		self.LEADER_BUTTON_SIZE = 64
		self.LEADER_MARGIN = 12

		self.bUnitDetails = False
		self.iShiftKeyDown = 0
		
						
	def getScreen(self):
		return CyGInterfaceScreen(self.MILITARY_SCREEN_NAME, self.screenId)

	def hideScreen(self):
		screen = self.getScreen()
		screen.hideScreen()
										
	# Screen construction function
	def interfaceScreen(self):
							
		# Create a new screen
		screen = self.getScreen()
		if screen.isActive():
			return
		screen.setRenderInterfaceOnly(True);
		screen.showScreen(PopupStates.POPUPSTATE_IMMEDIATE, False)

		self.EXIT_TEXT = u"<font=4>" + localText.getText("TXT_KEY_PEDIA_SCREEN_EXIT", ()).upper() + "</font>"
		self.TITLE = u"<font=4b>" + localText.getText("TXT_KEY_MILITARY_ADVISOR_TITLE", ()).upper() + "</font>"

		self.nWidgetCount = 0

		# Size the screen off the real desktop resolution (same approach as the Domestic
		# Advisor) so it always fits, instead of a fixed virtual canvas that can overflow
		# on smaller displays.
		self.W_SCREEN = screen.getXResolution() - 30
		self.H_SCREEN = screen.getYResolution() - 250
		self.X_SCREEN = self.W_SCREEN / 2

		self.X_EXIT = self.W_SCREEN - 25
		self.Y_EXIT = self.H_SCREEN - 45

		self.X_GREAT_GENERAL_BAR = 20
		self.Y_GREAT_GENERAL_BAR = self.H_SCREEN - 38
		self.W_GREAT_GENERAL_BAR = 300
		self.H_GREAT_GENERAL_BAR = 30

		self.W_LEADERS = self.W_SCREEN - 2 * self.X_LEADERS
		self.LEADER_COLUMNS = int(self.W_LEADERS / (self.LEADER_BUTTON_SIZE + self.LEADER_MARGIN))

		# Unit list sits on the right, full height of the body (below the leader row,
		# above the bottom bar); the map takes the rest of the width on the left, capped
		# at 1.5x its original size and vertically centered in whatever space is left -
		# never bigger than the screen actually has room for.
		self.W_TEXT = 330
		iBodyTop = self.Y_LEADERS + self.H_LEADERS + self.MAP_MARGIN
		iBodyBottom = self.H_SCREEN - 55 - self.MAP_MARGIN
		iBodyHeight = iBodyBottom - iBodyTop

		self.X_MAP = 20
		self.W_MAP = min(int(580 * 1.5), self.W_SCREEN - self.X_MAP - self.MAP_MARGIN - self.W_TEXT - self.MAP_MARGIN)
		self.H_MAP_MAX = min(int(500 * 1.5), iBodyHeight)
		self.Y_MAP = iBodyTop + (iBodyHeight - self.H_MAP_MAX) / 2

		self.X_TEXT = self.X_MAP + self.W_MAP + self.MAP_MARGIN - 25
		self.Y_TEXT = iBodyTop
		self.H_TEXT = iBodyHeight

		# Two more columns to the right of the unit list, flush against it (no gap) and
		# against each other. The production list is a fixed, content-sized width like the
		# unit list; the reserved panel (nothing in it yet) is the elastic one that soaks up
		# whatever's left over to the screen's right edge - so narrowing either list to its
		# left only ever grows the reserved panel, never the other list.
		self.X_PRODUCTION = self.X_TEXT + self.W_TEXT
		self.W_PRODUCTION = 320
		self.Y_PRODUCTION = iBodyTop
		self.H_PRODUCTION = iBodyHeight

		self.X_RESERVED = self.X_PRODUCTION + self.W_PRODUCTION
		self.W_RESERVED = self.W_SCREEN - self.MAP_MARGIN - self.X_RESERVED
		self.Y_RESERVED = iBodyTop
		self.H_RESERVED = iBodyHeight

		# Set the background and exit button, and show the screen
		screen.setDimensions(15, 100, self.W_SCREEN, self.H_SCREEN)
		screen.addDDSGFC(self.BACKGROUND_ID, ArtFileMgr.getInterfaceArtInfo("MAINMENU_SLIDESHOW_LOAD").getPath(), 0, 0, self.W_SCREEN, self.H_SCREEN, WidgetTypes.WIDGET_GENERAL, -1, -1 )
		screen.addPanel( "TechTopPanel", u"", u"", True, False, 0, 0, self.W_SCREEN, 55, PanelStyles.PANEL_STYLE_TOPBAR )
		screen.addPanel( "TechBottomPanel", u"", u"", True, False, 0, self.H_SCREEN - 55, self.W_SCREEN, 55, PanelStyles.PANEL_STYLE_BOTTOMBAR )
		screen.showWindowBackground(False)
		screen.setText(self.EXIT_ID, "Background", self.EXIT_TEXT, CvUtil.FONT_RIGHT_JUSTIFY, self.X_EXIT, self.Y_EXIT, self.Z_CONTROLS, FontTypes.TITLE_FONT, WidgetTypes.WIDGET_CLOSE_SCREEN, -1, -1 )
												
		# Header...
		self.szHeader = self.getNextWidgetName()
		screen.setText(self.szHeader, "Background", self.TITLE, CvUtil.FONT_CENTER_JUSTIFY, self.X_SCREEN, self.Y_TITLE, self.Z_CONTROLS, FontTypes.TITLE_FONT, WidgetTypes.WIDGET_GENERAL, -1, -1)
		
		# Minimap initialization
		self.H_MAP = (self.W_MAP * CyMap().getGridHeight()) / CyMap().getGridWidth()
		if (self.H_MAP > self.H_MAP_MAX):
			self.W_MAP = (self.H_MAP_MAX * CyMap().getGridWidth()) / CyMap().getGridHeight()
			self.H_MAP = self.H_MAP_MAX
		screen.addPanel("", u"", "", False, False, self.X_MAP, self.Y_MAP, self.W_MAP, self.H_MAP, PanelStyles.PANEL_STYLE_MAIN)
		screen.initMinimap(self.X_MAP + self.MAP_MARGIN, self.X_MAP + self.W_MAP - self.MAP_MARGIN, self.Y_MAP + self.MAP_MARGIN, self.Y_MAP + self.H_MAP - self.MAP_MARGIN, self.Z_CONTROLS)
		screen.updateMinimapSection(False, False)

		self.W_MAP_INNER = self.W_MAP - 2 * self.MAP_MARGIN
		self.H_MAP_INNER = self.H_MAP - 2 * self.MAP_MARGIN

		# Dedicated draw-control canvas for the rally arrows, sized to exactly cover the
		# minimap's inner (margin-trimmed) rectangle - NOT the whole screen. addLineGFC needs
		# a real draw control as its parent (like CvForeignAdvisor's BACKGROUND_ID, which is
		# an addDrawControl); our own BACKGROUND_ID is a plain addDDSGFC image and silently
		# ignores lines attached to it. A screen-sized canvas here previously ate clicks meant
		# for the exit button and other widgets underneath it, so keep it scoped to the map.
		screen.addDrawControl(self.RALLY_CANVAS_ID, None, self.X_MAP + self.MAP_MARGIN, self.Y_MAP + self.MAP_MARGIN, self.W_MAP_INNER, self.H_MAP_INNER, WidgetTypes.WIDGET_GENERAL, -1, -1)
		screen.moveToFront(self.RALLY_CANVAS_ID)

		screen.updateMinimapColorFromMap(MinimapModeTypes.MINIMAPMODE_TERRITORY, 0.3)

		screen.setMinimapMode(MinimapModeTypes.MINIMAPMODE_MILITARY)
		
		iOldMode = CyInterface().getShowInterface()
		CyInterface().setShowInterface(InterfaceVisibility.INTERFACE_MINIMAP_ONLY)
		screen.updateMinimapVisibility()
		CyInterface().setShowInterface(iOldMode)
					
		self.iActivePlayer = gc.getGame().getActivePlayer()

		self.unitsList = [(0, 0, [], 0)] * gc.getNumUnitInfos()
		self.selectedUnitList = []
		self.selectedPlayerList.append(self.iActivePlayer)

		self.drawCombatExperience()

		self.refresh(true)

		self.refreshRallyArrows()

		self.drawReservedPanel()
		self.drawProductionList()
		
	def drawCombatExperience(self):
	
		if (gc.getPlayer(self.iActivePlayer).greatPeopleThreshold(true) > 0):
		
			iExperience = gc.getPlayer(self.iActivePlayer).getCombatExperience()
			
			screen = self.getScreen()
			screen.addStackedBarGFC(self.GREAT_GENERAL_BAR_ID, self.X_GREAT_GENERAL_BAR, self.Y_GREAT_GENERAL_BAR, self.W_GREAT_GENERAL_BAR, self.H_GREAT_GENERAL_BAR, InfoBarTypes.NUM_INFOBAR_TYPES, WidgetTypes.WIDGET_HELP_GREAT_GENERAL, -1, -1)
			screen.setStackedBarColors(self.GREAT_GENERAL_BAR_ID, InfoBarTypes.INFOBAR_STORED, gc.getInfoTypeForString("COLOR_GREAT_PEOPLE_STORED"))
			screen.setStackedBarColors(self.GREAT_GENERAL_BAR_ID, InfoBarTypes.INFOBAR_RATE, gc.getInfoTypeForString("COLOR_GREAT_PEOPLE_RATE"))
			screen.setStackedBarColors(self.GREAT_GENERAL_BAR_ID, InfoBarTypes.INFOBAR_RATE_EXTRA, gc.getInfoTypeForString("COLOR_EMPTY"))
			screen.setStackedBarColors(self.GREAT_GENERAL_BAR_ID, InfoBarTypes.INFOBAR_EMPTY, gc.getInfoTypeForString("COLOR_EMPTY"))
			screen.setBarPercentage(self.GREAT_GENERAL_BAR_ID, InfoBarTypes.INFOBAR_STORED, float(iExperience) / float(gc.getPlayer(self.iActivePlayer).greatPeopleThreshold(true)))
			screen.setLabel(self.GREAT_GENERAL_LABEL_ID, "", localText.getText("TXT_KEY_MISC_COMBAT_EXPERIENCE", ()), CvUtil.FONT_CENTER_JUSTIFY, self.X_GREAT_GENERAL_BAR + self.W_GREAT_GENERAL_BAR/2, self.Y_GREAT_GENERAL_BAR + 6, 0, FontTypes.GAME_FONT, WidgetTypes.WIDGET_HELP_GREAT_GENERAL, -1, -1)
					
																									
	# returns a unique ID for a widget in this screen
	def getNextWidgetName(self):
		szName = self.WIDGET_ID + str(self.nWidgetCount)
		self.nWidgetCount += 1
		return szName
																	
	# A unit type's combat strength for power-counting purposes: air strength for units
	# that only fight in the air (ground combat 0), ground strength otherwise.
	def getUnitTypeStrength(self, iUnitType):
		unitInfo = gc.getUnitInfo(iUnitType)
		if (unitInfo.getAirCombat() > 0 and unitInfo.getCombat() == 0):
			return unitInfo.getAirCombat()
		return unitInfo.getCombat()

	def resetMinimapColor(self):
		screen = self.getScreen()
		for iX in range(gc.getMap().getGridWidth()):
			for iY in range(gc.getMap().getGridHeight()):
				screen.setMinimapColor(MinimapModeTypes.MINIMAPMODE_MILITARY, iX, iY, -1, 0.6)
																				
	# handle the input for this screen...
	def handleInput (self, inputClass):
		if ( inputClass.getNotifyCode() == NotifyCode.NOTIFY_CLICKED and inputClass.getFunctionName() == self.UNIT_BUTTON_ID) :
			self.bUnitDetails = not self.bUnitDetails
			self.refreshUnitSelection(True)
		elif (inputClass.getNotifyCode() == NotifyCode.NOTIFY_CHARACTER):
			if (inputClass.getData() == int(InputTypes.KB_LSHIFT) or inputClass.getData() == int(InputTypes.KB_RSHIFT)):
				self.iShiftKeyDown = inputClass.getID()

		return 0

	# Converts a world plot to a pixel position local to the rally-arrow canvas, which is
	# sized and positioned to exactly cover the minimap's inner (margin-trimmed) rectangle.
	# The minimap renders a few extra columns of wrapped terrain duplicated past both the
	# left and right edges (cylindrical map wrap) - MAP_WRAP_PADDING corrects for that so
	# plots near the east/west edges don't land a tile or two off. It's an approximation
	# (observed as "about 3 tiles" of combined overlap) - adjust it here if arrows are still
	# off horizontally. There's no such wrap vertically, so Y needs no correction.
	def plotToMinimapXY(self, iPlotX, iPlotY, iGridWidth, iGridHeight):
		fPaddedWidth = iGridWidth + self.MAP_WRAP_PADDING
		fPctX = (iPlotX + 0.5 + self.MAP_WRAP_PADDING / 2.0) / fPaddedWidth
		fPctY = (iPlotY + 0.5) / float(iGridHeight)
		x = fPctX * self.W_MAP_INNER
		y = (1.0 - fPctY) * self.H_MAP_INNER
		return (int(x), int(y))

	# Draws a line plus a small V-shaped arrowhead at (x1, y1) pointing from (x0, y0).
	def drawRallyArrow(self, screen, x0, y0, x1, y1, color):
		szLine = self.RALLY_LINE_ID + str(self.nRallyLineCount)
		self.nRallyLineCount += 1
		screen.addLineGFC(self.RALLY_CANVAS_ID, szLine, x0, y0, x1, y1, color)

		dx = x1 - x0
		dy = y1 - y0
		fLen = math.sqrt(dx * dx + dy * dy)
		if (fLen < 1):
			return

		ux = dx / fLen
		uy = dy / fLen
		px = -uy
		py = ux

		iHeadLen = 8
		iHeadWidth = 4

		xBack = x1 - ux * iHeadLen
		yBack = y1 - uy * iHeadLen

		for (xSide, ySide) in [(xBack + px * iHeadWidth, yBack + py * iHeadWidth), (xBack - px * iHeadWidth, yBack - py * iHeadWidth)]:
			szHead = self.RALLY_LINE_ID + str(self.nRallyLineCount)
			self.nRallyLineCount += 1
			screen.addLineGFC(self.RALLY_CANVAS_ID, szHead, int(xSide), int(ySide), x1, y1, color)

	# Redraws one arrow per city that has a rally point assigned, from the city to its own
	# rally plot - different cities can point at different places.
	def refreshRallyArrows(self):
		screen = self.getScreen()

		for i in range(self.nRallyLineCount):
			screen.removeLineGFC(self.RALLY_CANVAS_ID, self.RALLY_LINE_ID + str(i))
		self.nRallyLineCount = 0

		if (self.iActivePlayer < 0):
			return

		iGridWidth = CyMap().getGridWidth()
		iGridHeight = CyMap().getGridHeight()
		color = gc.getInfoTypeForString("COLOR_YELLOW")

		player = gc.getPlayer(self.iActivePlayer)
		(loopCity, iter) = player.firstCity(false)
		while (loopCity):
			pRallyPlot = loopCity.getRallyPlot()
			if (pRallyPlot and not pRallyPlot.isNone()):
				x0, y0 = self.plotToMinimapXY(loopCity.getX(), loopCity.getY(), iGridWidth, iGridHeight)
				x1, y1 = self.plotToMinimapXY(pRallyPlot.getX(), pRallyPlot.getY(), iGridWidth, iGridHeight)
				self.drawRallyArrow(screen, x0, y0, x1, y1, color)
			(loopCity, iter) = player.nextCity(iter, false)

	# Just reserves the space for now - a more complex custom panel goes here later.
	def drawReservedPanel(self):
		screen = self.getScreen()
		screen.addPanel(self.RESERVED_PANEL_ID, "", "", True, False, self.X_RESERVED, self.Y_RESERVED, self.W_RESERVED, self.H_RESERVED, PanelStyles.PANEL_STYLE_MAIN)

	# Lists every city of the active player currently building a military unit (one whose
	# UnitCombatType isn't NONE - the same grouping the unit list above uses), with the unit
	# being built and turns left, soonest first.
	def drawProductionList(self):
		screen = self.getScreen()

		screen.addTableControlGFC(self.PRODUCTION_LIST_ID, 3, self.X_PRODUCTION, self.Y_PRODUCTION, self.W_PRODUCTION, self.H_PRODUCTION, True, False, 24, 24, TableStyles.TABLE_STYLE_STANDARD)
		screen.enableSelect(self.PRODUCTION_LIST_ID, True)
		screen.setStyle(self.PRODUCTION_LIST_ID, "Table_StandardCiv_Style")

		iTurnsWidth = 60
		iNameWidth = (self.W_PRODUCTION - iTurnsWidth) / 2
		iUnitWidth = self.W_PRODUCTION - iNameWidth - iTurnsWidth
		screen.setTableColumnHeader(self.PRODUCTION_LIST_ID, COLUMN_PRODUCTION_CITY, localText.getText("TXT_KEY_DOMESTIC_ADVISOR_NAME", ()), iNameWidth)
		screen.setTableColumnHeader(self.PRODUCTION_LIST_ID, COLUMN_PRODUCTION_UNIT, localText.getText("TXT_KEY_UTOPIA_MILITARY_PRODUCTION_UNIT_HEADER", ()), iUnitWidth)
		screen.setTableColumnHeader(self.PRODUCTION_LIST_ID, COLUMN_PRODUCTION_TURNS, localText.getText("TXT_KEY_UTOPIA_MILITARY_PRODUCTION_TURNS_HEADER", ()), iTurnsWidth)

		rows = []
		player = gc.getPlayer(self.iActivePlayer)
		(loopCity, iter) = player.firstCity(false)
		while (loopCity):
			if (loopCity.isProductionUnit()):
				eUnit = loopCity.getProductionUnit()
				if (gc.getUnitInfo(eUnit).getUnitCombatType() != -1):
					rows.append((loopCity.getProductionTurnsLeft(), loopCity.getName(), gc.getUnitInfo(eUnit).getDescription()))
			(loopCity, iter) = player.nextCity(iter, false)

		rows.sort()

		for i in range(len(rows)):
			(iTurns, szCityName, szUnitName) = rows[i]
			screen.appendTableRow(self.PRODUCTION_LIST_ID)
			screen.setTableText(self.PRODUCTION_LIST_ID, COLUMN_PRODUCTION_CITY, i, szCityName, "", WidgetTypes.WIDGET_GENERAL, -1, -1, CvUtil.FONT_LEFT_JUSTIFY)
			screen.setTableText(self.PRODUCTION_LIST_ID, COLUMN_PRODUCTION_UNIT, i, szUnitName, "", WidgetTypes.WIDGET_GENERAL, -1, -1, CvUtil.FONT_LEFT_JUSTIFY)
			screen.setTableInt(self.PRODUCTION_LIST_ID, COLUMN_PRODUCTION_TURNS, i, unicode(iTurns), "", WidgetTypes.WIDGET_GENERAL, -1, -1, CvUtil.FONT_RIGHT_JUSTIFY)

	def update(self, fDelta):
		screen = self.getScreen()
		screen.updateMinimap(fDelta)

	def minimapClicked(self):
		pass
						
	def isSelectedGroup(self, iGroup, bIndirect):
		if (bIndirect):
			if -1 in self.selectedGroupList:
				return True
			if iGroup == -1:
				return False
		return ((iGroup + gc.getNumUnitInfos()) in self.selectedGroupList)
				
	def isSelectedUnitType(self, iUnit, bIndirect):
		if (bIndirect):
			if -1 in self.selectedGroupList:
				return True
			if self.isSelectedGroup(gc.getUnitInfo(iUnit).getUnitCombatType(), True):
				return True
		return (iUnit in self.selectedGroupList)
		
	def isSelectedUnit(self, iPlayer, iUnitId, bIndirect):
		if (bIndirect):
			if -1 in self.selectedGroupList:
				return True
			unit = gc.getPlayer(iPlayer).getUnit(iUnitId)
			if self.isSelectedGroup(gc.getUnitInfo(unit.getUnitType()).getUnitCombatType(), True):
				return True
			if self.isSelectedUnitType(unit.getUnitType(), True):
				return True
		return ((iPlayer, iUnitId) in self.selectedUnitList)
		
	def refreshSelectedLeader(self, iPlayer):
		if self.iShiftKeyDown == 1:
			if (iPlayer in self.selectedPlayerList):
				self.selectedPlayerList.remove(iPlayer)
			else:
				self.selectedPlayerList.append(iPlayer)
		else:
			self.selectedPlayerList = []
			self.selectedPlayerList.append(iPlayer)	
	
		self.refresh(True)
				
	def getLeaderButton(self, iPlayer):
		szName = self.LEADER_BUTTON_ID + str(iPlayer)
		return szName

	def refreshSelectedGroup(self, iSelected):
		if (iSelected in self.selectedGroupList):
			self.selectedGroupList.remove(iSelected)
		else:
			self.selectedGroupList.append(iSelected)
		self.refreshUnitSelection(false)
			
	def refreshSelectedUnit(self, iPlayer, iUnitId):
		selectedUnit = (iPlayer, iUnitId)
		if (selectedUnit in self.selectedUnitList):
			self.selectedUnitList.remove(selectedUnit)
		else:
			self.selectedUnitList.append(selectedUnit)
		self.refreshUnitSelection(false)		
	
	def refreshUnitSelection(self, bReload):
		screen = self.getScreen()
		
		screen.minimapClearAllFlashingTiles()

		if (bReload):
			if (self.bUnitDetails):
				screen.setButtonGFC(self.UNIT_BUTTON_ID, u"", "", self.X_TEXT + self.MAP_MARGIN, self.Y_TEXT + self.MAP_MARGIN/2, 20, 20, WidgetTypes.WIDGET_GENERAL, -1, -1, ButtonStyles.BUTTON_STYLE_CITY_MINUS )
				screen.setLabel(self.UNIT_BUTTON_LABEL_ID, "", localText.getText("TXT_KEY_MILITARY_ADVISOR_UNIT_TOGGLE_OFF", ()), CvUtil.FONT_LEFT_JUSTIFY, self.X_TEXT + self.MAP_MARGIN + 22, self.Y_TEXT + self.MAP_MARGIN/2 + 2, 0, FontTypes.GAME_FONT, WidgetTypes.WIDGET_GENERAL, -1, -1)
			else:
				screen.setButtonGFC(self.UNIT_BUTTON_ID, u"", "", self.X_TEXT + self.MAP_MARGIN, self.Y_TEXT + self.MAP_MARGIN/2, 20, 20, WidgetTypes.WIDGET_GENERAL, -1, -1, ButtonStyles.BUTTON_STYLE_CITY_PLUS )
				screen.setLabel(self.UNIT_BUTTON_LABEL_ID, "", localText.getText("TXT_KEY_MILITARY_ADVISOR_UNIT_TOGGLE_ON", ()), CvUtil.FONT_LEFT_JUSTIFY, self.X_TEXT + self.MAP_MARGIN + 22, self.Y_TEXT + self.MAP_MARGIN/2 + 2, 0, FontTypes.GAME_FONT, WidgetTypes.WIDGET_GENERAL, -1, -1)

		# self.unitsList[iUnit][0] is the UnitCombatGroup (e.g. Melee)
		# self.unitsList[iUnit][1] is the unit type (e.g. Warrior)
		# self.unitsList[iUnit][2] is a list of the active player's actual units
		# self.unitsList[iUnit][3] is the total number of those units seen by the active player (not only his own)
		
		if bReload:
			for iUnit in range(gc.getNumUnitInfos()):
				self.unitsList[iUnit] = (gc.getUnitInfo(iUnit).getUnitCombatType(), iUnit, [], 0)

			for iPlayer in range(gc.getMAX_PLAYERS()):			
				player = PyPlayer(iPlayer)
				if (player.isAlive()):
					unitList = player.getUnitList()
					for loopUnit in unitList:
						unitType = loopUnit.getUnitType()
						
						bVisible = False
						plot = loopUnit.plot()
						if (not plot.isNone()):
							bVisible = plot.isVisible(gc.getPlayer(self.iActivePlayer).getTeam(), False) and not loopUnit.isInvisible(gc.getPlayer(self.iActivePlayer).getTeam(), False)

						if unitType >= 0 and unitType < gc.getNumUnitInfos() and bVisible:
							iNumUnits = self.unitsList[unitType][3]
							if (iPlayer == self.iActivePlayer):
								iNumUnits += 1
							if loopUnit.getVisualOwner() in self.selectedPlayerList:
								self.unitsList[unitType][2].append(loopUnit)							
							
							self.unitsList[unitType] = (self.unitsList[unitType][0], self.unitsList[unitType][1], self.unitsList[unitType][2], iNumUnits)

			# sort by unit combat type
			self.unitsList.sort()
		
		# Total military power of everything currently listed below (sum of count * strength
		# per unit type) - computed ourselves rather than trusting any built-in power value,
		# since there isn't one that matches what's actually on screen.
		iTotalPower = 0
		for iUnit in range(gc.getNumUnitInfos()):
			iCount = len(self.unitsList[iUnit][2])
			if (iCount > 0):
				iTotalPower += iCount * self.getUnitTypeStrength(self.unitsList[iUnit][1])

		szText = localText.getText("TXT_KEY_PEDIA_ALL_UNITS", ()).upper() + u" " + unicode(iTotalPower) + u"%c" % CyGame().getSymbolID(FontSymbols.STRENGTH_CHAR)
		if (-1 in self.selectedGroupList):
			szText = localText.changeTextColor(u"<u>" + szText + u"</u>", gc.getInfoTypeForString("COLOR_YELLOW"))
		if (bReload):
			screen.addListBoxGFC(self.UNIT_LIST_ID, "", self.X_TEXT+self.MAP_MARGIN, self.Y_TEXT+self.MAP_MARGIN+15, self.W_TEXT-2*self.MAP_MARGIN, self.H_TEXT-2*self.MAP_MARGIN-15, TableStyles.TABLE_STYLE_STANDARD)
			screen.enableSelect(self.UNIT_LIST_ID, False)
			screen.setStyle(self.UNIT_LIST_ID, "Table_StandardCiv_Style")
			screen.appendListBoxString(self.UNIT_LIST_ID, szText, WidgetTypes.WIDGET_MINIMAP_HIGHLIGHT, 1, -1, CvUtil.FONT_LEFT_JUSTIFY)
		else:		
			screen.setListBoxStringGFC(self.UNIT_LIST_ID, 0, szText, WidgetTypes.WIDGET_MINIMAP_HIGHLIGHT, 1, -1, CvUtil.FONT_LEFT_JUSTIFY)

		iPrevUnitCombat = -2
		iItem = 1
		for iUnit in range(gc.getNumUnitInfos()):
			if (len(self.unitsList[iUnit][2]) > 0):
				if (iPrevUnitCombat != self.unitsList[iUnit][0] and self.unitsList[iUnit][0] != -1):
					iPrevUnitCombat = self.unitsList[iUnit][0]
					szDescription = gc.getUnitCombatInfo(self.unitsList[iUnit][0]).getDescription().upper()
					if (self.isSelectedGroup(self.unitsList[iUnit][0], False)):
						szDescription = u"   <u>" + szDescription + u"</u>"
					else:
						szDescription = u"   " + szDescription
					if (self.isSelectedGroup(self.unitsList[iUnit][0], True)):
						szDescription = localText.changeTextColor(szDescription, gc.getInfoTypeForString("COLOR_YELLOW"))
					if (bReload):
						screen.appendListBoxString(self.UNIT_LIST_ID, szDescription, WidgetTypes.WIDGET_MINIMAP_HIGHLIGHT, 1, self.unitsList[iUnit][0] + gc.getNumUnitInfos(), CvUtil.FONT_LEFT_JUSTIFY)
					else:
						screen.setListBoxStringGFC(self.UNIT_LIST_ID, iItem, szDescription, WidgetTypes.WIDGET_MINIMAP_HIGHLIGHT, 1, self.unitsList[iUnit][0] + gc.getNumUnitInfos(), CvUtil.FONT_LEFT_JUSTIFY)
					iItem += 1
				
				unitInfo = gc.getUnitInfo(self.unitsList[iUnit][1])
				iStrength = self.getUnitTypeStrength(self.unitsList[iUnit][1])
				szDescription = unitInfo.getDescription() + u" " + unicode(iStrength) + u"%c" % CyGame().getSymbolID(FontSymbols.STRENGTH_CHAR) + u" " + unicode(unitInfo.getMoves()) + u"%c" % CyGame().getSymbolID(FontSymbols.MOVES_CHAR) + u" (" + unicode(len(self.unitsList[iUnit][2])) + u")"
				if (self.isSelectedUnitType(self.unitsList[iUnit][1], False)):
					szDescription = u"      <u>" + szDescription + u"</u>"
				else:
					szDescription = u"      " + szDescription
				if (self.isSelectedUnitType(self.unitsList[iUnit][1], True)):
					szDescription = localText.changeTextColor(szDescription, gc.getInfoTypeForString("COLOR_YELLOW"))
				if (bReload):
					screen.appendListBoxString(self.UNIT_LIST_ID, szDescription, WidgetTypes.WIDGET_MINIMAP_HIGHLIGHT, 1, self.unitsList[iUnit][1], CvUtil.FONT_LEFT_JUSTIFY)
				else:
					screen.setListBoxStringGFC(self.UNIT_LIST_ID, iItem, szDescription, WidgetTypes.WIDGET_MINIMAP_HIGHLIGHT, 1, self.unitsList[iUnit][1], CvUtil.FONT_LEFT_JUSTIFY)
				iItem += 1
				
				for loopUnit in self.unitsList[iUnit][2]:
				
					if (self.bUnitDetails):
						szDescription = CyGameTextMgr().getSpecificUnitHelp(loopUnit, true, false)

						listMatches = re.findall("<.*?color.*?>", szDescription)	
						for szMatch in listMatches:
							szDescription = szDescription.replace(szMatch, u"")
						
						if (loopUnit.isWaiting()):
							szDescription = '*' + szDescription
							
						if (self.isSelectedUnit(loopUnit.getOwner(), loopUnit.getID(), False)):
							szDescription = u"         <u>" + szDescription + u"</u>"
						else:
							szDescription = u"         " + szDescription

						if (self.isSelectedUnit(loopUnit.getOwner(), loopUnit.getID(), True)):
							szDescription = localText.changeTextColor(szDescription, gc.getInfoTypeForString("COLOR_YELLOW"))

						if (bReload):
							screen.appendListBoxString(self.UNIT_LIST_ID, szDescription, WidgetTypes.WIDGET_MINIMAP_HIGHLIGHT, -loopUnit.getOwner(), loopUnit.getID(), CvUtil.FONT_LEFT_JUSTIFY)
						else:
							screen.setListBoxStringGFC(self.UNIT_LIST_ID, iItem, szDescription, WidgetTypes.WIDGET_MINIMAP_HIGHLIGHT, -loopUnit.getOwner(), loopUnit.getID(), CvUtil.FONT_LEFT_JUSTIFY)
						iItem += 1

					iPlayer = loopUnit.getVisualOwner()
					player = PyPlayer(iPlayer)
					iColor = gc.getPlayerColorInfo(gc.getPlayer(iPlayer).getPlayerColor()).getColorTypePrimary()
					screen.setMinimapColor(MinimapModeTypes.MINIMAPMODE_MILITARY, loopUnit.getX(), loopUnit.getY(), iColor, 0.6)
					if (self.isSelectedUnit(loopUnit.getOwner(), loopUnit.getID(), True) and (iPlayer in self.selectedPlayerList)):
						
						if (player.getTeam().isAtWar(gc.getPlayer(self.iActivePlayer).getTeam())):
							iColor = gc.getInfoTypeForString("COLOR_RED")
						elif (gc.getPlayer(iPlayer).getTeam() != gc.getPlayer(self.iActivePlayer).getTeam()):
							iColor = gc.getInfoTypeForString("COLOR_YELLOW")
						else:
							iColor = gc.getInfoTypeForString("COLOR_WHITE")
						screen.minimapFlashPlot(loopUnit.getX(), loopUnit.getY(), iColor, -1)

					
	
	def refresh(self, bReload):
	
		if (self.iActivePlayer < 0):
			return
						
		screen = self.getScreen()
				
		if (bReload):
			# Set scrollable area for unit buttons
			screen.addPanel(self.UNIT_PANEL_ID, "", "", True, True, self.X_TEXT, self.Y_TEXT, self.W_TEXT, self.H_TEXT, PanelStyles.PANEL_STYLE_MAIN)
			
			# Set scrollable area for leaders
			screen.addPanel(self.LEADER_PANEL_ID, "", "", False, True, self.X_LEADERS, self.Y_LEADERS, self.W_LEADERS, self.H_LEADERS, PanelStyles.PANEL_STYLE_MAIN)

		listLeaders = []
		for iLoopPlayer in range(gc.getMAX_PLAYERS()):
			player = gc.getPlayer(iLoopPlayer)
			if (player.isAlive() and (gc.getTeam(player.getTeam()).isHasMet(gc.getPlayer(self.iActivePlayer).getTeam()) or gc.getGame().isDebugMode())):
				listLeaders.append(iLoopPlayer)
				
		iNumLeaders = len(listLeaders)
		if iNumLeaders >= self.LEADER_COLUMNS:
			iButtonSize = self.LEADER_BUTTON_SIZE / 2
		else:
			iButtonSize = self.LEADER_BUTTON_SIZE

		iColumns = int(self.W_LEADERS / (iButtonSize + self.LEADER_MARGIN))

		# loop through all players and display leaderheads
		for iIndex in range(iNumLeaders):
			iLoopPlayer = listLeaders[iIndex]
			player = gc.getPlayer(iLoopPlayer)
			
			x = self.X_LEADERS + self.LEADER_MARGIN + (iIndex % iColumns) * (iButtonSize + self.LEADER_MARGIN)
			y = self.Y_LEADERS + self.LEADER_MARGIN + (iIndex // iColumns) * (iButtonSize + self.LEADER_MARGIN)

			if (bReload):
				if player.isBarbarian():
					szButton = "Art/Interface/Buttons/Civilizations/Barbarian.dds"
				else:
					szButton = gc.getLeaderHeadInfo(gc.getPlayer(iLoopPlayer).getLeaderType()).getButton()
				screen.addCheckBoxGFC(self.getLeaderButton(iLoopPlayer), szButton, ArtFileMgr.getInterfaceArtInfo("BUTTON_HILITE_SQUARE").getPath(), x, y, iButtonSize, iButtonSize, WidgetTypes.WIDGET_MINIMAP_HIGHLIGHT, 2, iLoopPlayer, ButtonStyles.BUTTON_STYLE_LABEL)
				screen.setState(self.getLeaderButton(iLoopPlayer), (iLoopPlayer in self.selectedPlayerList))				
		
		self.refreshUnitSelection(bReload)
		
		
		
		
		