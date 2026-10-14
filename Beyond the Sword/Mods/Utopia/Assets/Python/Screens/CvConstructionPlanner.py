## Utopia mod - Construction Planner
## Lets the player pick a subset of cities and a regular building, then push that
## building onto all of them at once (build now / queue at end / queue at front).
##
## Only the city list is a real GFC table - running two addTableControlGFC tables in
## the same screen turned out unreliable, so the building list is instead a small
## fixed set of manually laid out rows (icon + name + cost) that we scroll ourselves
## with two arrow buttons, redrawing the visible window in place.
from CvPythonExtensions import *
import CvUtil
import CvScreenEnums

gc = CyGlobalContext()
localText = CyTranslator()

SCREEN_NAME = "ConstructionPlanner"

CITY_TABLE_NAME = "ConstructionPlannerCityList"
COLUMN_CHECK = 0
COLUMN_NAME = 1
COLUMN_HAMMERS = 2

CHECK_MARK_TEXT = u"[x]"
CHECK_EMPTY_TEXT = u"[ ]"

VISIBLE_BUILDING_ROWS = 12
BUILDING_ROW_HEIGHT = 36
BUILDING_ICON_SIZE = 32
BUILDING_COST_WIDTH = 70
BUILDING_SCROLL_STRIP_WIDTH = 30

class CvConstructionPlanner:
	"Construction Planner Screen"
	def __init__(self):
		self.selectedCityIDs = set()
		self.selectedBuildingType = -1
		self.buildableBuildings = []
		self.iBuildScrollOffset = 0
		self.iActivePlayer = -1

	# Screen construction function
	def interfaceScreen(self):
		screen = CyGInterfaceScreen( SCREEN_NAME, CvScreenEnums.CONSTRUCTION_PLANNER )

		self.iActivePlayer = gc.getGame().getActivePlayer()
		self.buildableBuildings = self.computeBuildableBuildings()
		self.iBuildScrollOffset = 0

		self.nScreenWidth = 900
		self.nScreenHeight = 620

		self.nListX = 20
		self.nListWidth = 330
		self.nListY = 95
		self.nListHeight = self.nScreenHeight - self.nListY - 60

		self.nBuildX = self.nListX + self.nListWidth + 24
		self.nBuildWidth = self.nScreenWidth - self.nBuildX - 20
		self.nBuildContentWidth = self.nBuildWidth - BUILDING_SCROLL_STRIP_WIDTH - 6
		self.nBuildNameWidth = self.nBuildContentWidth - BUILDING_ICON_SIZE - 8 - BUILDING_COST_WIDTH - 8

		screen.setRenderInterfaceOnly(True)
		screen.setDimensions(100, 100, self.nScreenWidth, self.nScreenHeight)
		screen.showScreen(PopupStates.POPUPSTATE_IMMEDIATE, False)

		screen.addPanel( "ConstructionPlannerBG", u"", u"", True, False, 0, 0, self.nScreenWidth, self.nScreenHeight, PanelStyles.PANEL_STYLE_MAIN )

		screen.setLabel( "ConstructionPlannerTitle", "Background", localText.getText("TXT_KEY_UTOPIA_CONSTRUCTION_PLANNER", ()), CvUtil.FONT_LEFT_JUSTIFY, self.nListX, 20, -0.1, FontTypes.TITLE_FONT, WidgetTypes.WIDGET_GENERAL, -1, -1 )

		# Select All / Reset All - above the city list
		iHalfWidth = (self.nListWidth - 8) / 2
		screen.setButtonGFC( "ConstructionPlannerSelectAll", localText.getText("TXT_KEY_UTOPIA_SELECT_ALL_CITIES", ()), "", self.nListX, 55, iHalfWidth, 26, WidgetTypes.WIDGET_GENERAL, -1, -1, ButtonStyles.BUTTON_STYLE_STANDARD )
		screen.setButtonGFC( "ConstructionPlannerResetAll", localText.getText("TXT_KEY_UTOPIA_RESET_ALL_CITIES", ()), "", self.nListX + iHalfWidth + 8, 55, iHalfWidth, 26, WidgetTypes.WIDGET_GENERAL, -1, -1, ButtonStyles.BUTTON_STYLE_STANDARD )

		# City list - checkbox + name + hammers/turn, click anywhere on a row to toggle it
		screen.addTableControlGFC( CITY_TABLE_NAME, 3, self.nListX, self.nListY, self.nListWidth, self.nListHeight, True, False, 24, 24, TableStyles.TABLE_STYLE_STANDARD )
		screen.enableSelect( CITY_TABLE_NAME, True )
		screen.setStyle( CITY_TABLE_NAME, "Table_StandardCiv_Style" )
		screen.setTableColumnHeader( CITY_TABLE_NAME, COLUMN_CHECK, "", 40 )
		screen.setTableColumnHeader( CITY_TABLE_NAME, COLUMN_NAME, localText.getText("TXT_KEY_DOMESTIC_ADVISOR_NAME", ()), self.nListWidth - 40 - 55 )
		screen.setTableColumnHeader( CITY_TABLE_NAME, COLUMN_HAMMERS, "<font=2>" + (u"%c" % gc.getYieldInfo(YieldTypes.YIELD_PRODUCTION).getChar()) + "</font>", 55 )

		# Build-order action buttons - above the building list
		iActionWidth = (self.nBuildWidth - 16) / 3
		screen.setButtonGFC( "ConstructionPlannerBuildNow", localText.getText("TXT_KEY_UTOPIA_BUILD_NOW", ()), "", self.nBuildX, 55, iActionWidth, 26, WidgetTypes.WIDGET_GENERAL, -1, -1, ButtonStyles.BUTTON_STYLE_STANDARD )
		screen.setButtonGFC( "ConstructionPlannerQueueEnd", localText.getText("TXT_KEY_UTOPIA_QUEUE_AT_END", ()), "", self.nBuildX + iActionWidth + 8, 55, iActionWidth, 26, WidgetTypes.WIDGET_GENERAL, -1, -1, ButtonStyles.BUTTON_STYLE_STANDARD )
		screen.setButtonGFC( "ConstructionPlannerQueueFront", localText.getText("TXT_KEY_UTOPIA_QUEUE_AT_FRONT", ()), "", self.nBuildX + 2 * (iActionWidth + 8), 55, iActionWidth, 26, WidgetTypes.WIDGET_GENERAL, -1, -1, ButtonStyles.BUTTON_STYLE_STANDARD )

		# Scroll arrows for the building list, stacked on its right edge
		iScrollX = self.nBuildX + self.nBuildContentWidth + 6
		screen.setButtonGFC( "ConstructionPlannerBuildScrollUp", u"", "", iScrollX, self.nListY, BUILDING_SCROLL_STRIP_WIDTH, 30, WidgetTypes.WIDGET_GENERAL, -1, -1, ButtonStyles.BUTTON_STYLE_ARROW_LEFT )
		screen.setButtonGFC( "ConstructionPlannerBuildScrollDown", u"", "", iScrollX, self.nListY + self.nListHeight - 30, BUILDING_SCROLL_STRIP_WIDTH, 30, WidgetTypes.WIDGET_GENERAL, -1, -1, ButtonStyles.BUTTON_STYLE_ARROW_RIGHT )

		# Building rows - created once, hidden/shown and re-filled as we scroll
		for iSlot in range(VISIBLE_BUILDING_ROWS):
			iRowY = self.nListY + iSlot * BUILDING_ROW_HEIGHT
			screen.setImageButton( self.getSlotIconName(iSlot), "", self.nBuildX, iRowY, BUILDING_ICON_SIZE, BUILDING_ICON_SIZE, WidgetTypes.WIDGET_GENERAL, -1, -1 )
			screen.setText( self.getSlotNameName(iSlot), "Background", u"", CvUtil.FONT_LEFT_JUSTIFY, self.nBuildX + BUILDING_ICON_SIZE + 8, iRowY + 6, -0.1, FontTypes.SMALL_FONT, WidgetTypes.WIDGET_GENERAL, -1, -1 )
			screen.setLabel( self.getSlotCostName(iSlot), "Background", u"", CvUtil.FONT_RIGHT_JUSTIFY, self.nBuildX + BUILDING_ICON_SIZE + 8 + self.nBuildNameWidth + 8, iRowY + 6, -0.1, FontTypes.SMALL_FONT, WidgetTypes.WIDGET_GENERAL, -1, -1 )

		# Close button, bottom right - same style as the other advisor screens
		screen.setText( "ConstructionPlannerClose", "Background", localText.getText("TXT_KEY_PEDIA_SCREEN_EXIT", ()).upper(), CvUtil.FONT_RIGHT_JUSTIFY, self.nScreenWidth - 25, self.nScreenHeight - 35, -0.1, FontTypes.TITLE_FONT, WidgetTypes.WIDGET_CLOSE_SCREEN, -1, -1 )

		self.drawCityList()
		self.refreshBuildingSlots()

	def getSlotIconName(self, iSlot):
		return "ConstructionPlannerBuildIcon" + str(iSlot)

	def getSlotNameName(self, iSlot):
		return "ConstructionPlannerBuildName" + str(iSlot)

	def getSlotCostName(self, iSlot):
		return "ConstructionPlannerBuildCost" + str(iSlot)

	# Every regular (non-wonder, non-small-wonder) building the player could ever build,
	# regardless of whether any one particular city currently meets its requirements.
	def computeBuildableBuildings(self):
		player = gc.getPlayer(self.iActivePlayer)
		eCiv = player.getCivilizationType()
		listBuildings = []
		for iBuildingClass in range(gc.getNumBuildingClassInfos()):
			if isLimitedWonderClass(iBuildingClass):
				continue
			eBuilding = gc.getCivilizationInfo(eCiv).getCivilizationBuildings(iBuildingClass)
			if eBuilding == -1:
				continue
			if player.canConstruct(eBuilding, False, True, False):
				listBuildings.append(eBuilding)
		return listBuildings

	# Builds the city rows once per screen open - row count doesn't change afterwards,
	# only the checkbox cell content gets refreshed in place.
	def drawCityList(self):
		screen = CyGInterfaceScreen( SCREEN_NAME, CvScreenEnums.CONSTRUCTION_PLANNER )
		player = gc.getPlayer(self.iActivePlayer)

		i = 0
		(pLoopCity, iter) = player.firstCity(false)
		while(pLoopCity):
			screen.appendTableRow( CITY_TABLE_NAME )
			self.updateCheckboxCell(i, pLoopCity.getID(), pLoopCity.getID() in self.selectedCityIDs)
			screen.setTableText( CITY_TABLE_NAME, COLUMN_NAME, i, pLoopCity.getName(), "", WidgetTypes.WIDGET_GENERAL, self.iActivePlayer, pLoopCity.getID(), CvUtil.FONT_LEFT_JUSTIFY )
			screen.setTableInt( CITY_TABLE_NAME, COLUMN_HAMMERS, i, unicode(pLoopCity.getYieldRate(YieldTypes.YIELD_PRODUCTION)), "", WidgetTypes.WIDGET_GENERAL, self.iActivePlayer, pLoopCity.getID(), CvUtil.FONT_RIGHT_JUSTIFY )
			i += 1
			(pLoopCity, iter) = player.nextCity(iter, false)

	# Redraws just the checkbox column, used after Select All / Reset All
	def refreshCheckboxColumn(self):
		player = gc.getPlayer(self.iActivePlayer)

		i = 0
		(pLoopCity, iter) = player.firstCity(false)
		while(pLoopCity):
			self.updateCheckboxCell(i, pLoopCity.getID(), pLoopCity.getID() in self.selectedCityIDs)
			i += 1
			(pLoopCity, iter) = player.nextCity(iter, false)

	def updateCheckboxCell(self, iRow, iCityID, bChecked):
		screen = CyGInterfaceScreen( SCREEN_NAME, CvScreenEnums.CONSTRUCTION_PLANNER )
		if bChecked:
			szCheck = CHECK_MARK_TEXT
		else:
			szCheck = CHECK_EMPTY_TEXT
		screen.setTableText( CITY_TABLE_NAME, COLUMN_CHECK, iRow, szCheck, "", WidgetTypes.WIDGET_GENERAL, self.iActivePlayer, iCityID, CvUtil.FONT_CENTER_JUSTIFY )

	def selectAllCities(self):
		player = gc.getPlayer(self.iActivePlayer)
		(pLoopCity, iter) = player.firstCity(false)
		while(pLoopCity):
			self.selectedCityIDs.add(pLoopCity.getID())
			(pLoopCity, iter) = player.nextCity(iter, false)
		self.refreshCheckboxColumn()

	def resetAllCities(self):
		self.selectedCityIDs = set()
		self.refreshCheckboxColumn()

	# Redraws the fixed window of visible building slots at the current scroll offset
	def refreshBuildingSlots(self):
		screen = CyGInterfaceScreen( SCREEN_NAME, CvScreenEnums.CONSTRUCTION_PLANNER )
		iTotal = len(self.buildableBuildings)

		for iSlot in range(VISIBLE_BUILDING_ROWS):
			iBuildingIndex = self.iBuildScrollOffset + iSlot
			szIconName = self.getSlotIconName(iSlot)
			szNameName = self.getSlotNameName(iSlot)
			szCostName = self.getSlotCostName(iSlot)

			if (iBuildingIndex >= iTotal):
				screen.hide(szIconName)
				screen.hide(szNameName)
				screen.hide(szCostName)
				continue

			eBuilding = self.buildableBuildings[iBuildingIndex]
			pBuildingInfo = gc.getBuildingInfo(eBuilding)

			screen.setImageButton( szIconName, pBuildingInfo.getButton(), self.nBuildX, self.nListY + iSlot * BUILDING_ROW_HEIGHT, BUILDING_ICON_SIZE, BUILDING_ICON_SIZE, WidgetTypes.WIDGET_GENERAL, eBuilding, -1 )
			screen.show(szIconName)

			szName = pBuildingInfo.getDescription()
			if (eBuilding == self.selectedBuildingType):
				szName = localText.getText("TXT_KEY_COLOR_POSITIVE", ()) + szName + localText.getText("TXT_KEY_COLOR_REVERT", ())
			screen.setText( szNameName, "Background", szName, CvUtil.FONT_LEFT_JUSTIFY, self.nBuildX + BUILDING_ICON_SIZE + 8, self.nListY + iSlot * BUILDING_ROW_HEIGHT + 6, -0.1, FontTypes.SMALL_FONT, WidgetTypes.WIDGET_GENERAL, eBuilding, -1 )
			screen.show(szNameName)

			screen.setLabel( szCostName, "Background", unicode(pBuildingInfo.getProductionCost()), CvUtil.FONT_RIGHT_JUSTIFY, self.nBuildX + BUILDING_ICON_SIZE + 8 + self.nBuildNameWidth + 8, self.nListY + iSlot * BUILDING_ROW_HEIGHT + 6, -0.1, FontTypes.SMALL_FONT, WidgetTypes.WIDGET_GENERAL, -1, -1 )
			screen.show(szCostName)

	def scrollBuildingList(self, iDirection):
		iMaxOffset = max(0, len(self.buildableBuildings) - VISIBLE_BUILDING_ROWS)
		iNewOffset = self.iBuildScrollOffset + iDirection
		if iNewOffset < 0:
			iNewOffset = 0
		elif iNewOffset > iMaxOffset:
			iNewOffset = iMaxOffset
		if iNewOffset != self.iBuildScrollOffset:
			self.iBuildScrollOffset = iNewOffset
			self.refreshBuildingSlots()

	def selectBuilding(self, eBuilding):
		if (eBuilding == self.selectedBuildingType):
			return
		self.selectedBuildingType = eBuilding
		self.refreshBuildingSlots()

	# Pushes the selected building onto every selected city's order queue.
	# bShift/bCtrl match the real key-held meaning used by the native city screen:
	# neither -> replace current production, bShift -> queue at the end,
	# bCtrl -> insert at the front without dropping whatever was being built.
	def applyBuildOrder(self, bShift, bCtrl):
		if (self.selectedBuildingType == -1 or len(self.selectedCityIDs) == 0):
			return
		for iCityID in self.selectedCityIDs:
			CyMessageControl().sendPushOrder(iCityID, OrderTypes.ORDER_CONSTRUCT, self.selectedBuildingType, False, bShift, bCtrl)

	# Will handle the input for this screen...
	def handleInput (self, inputClass):
		if ( inputClass.getNotifyCode() == NotifyCode.NOTIFY_LISTBOX_ITEM_SELECTED ):
			iCityID = inputClass.getData2()
			if (iCityID != -1):
				if iCityID in self.selectedCityIDs:
					self.selectedCityIDs.discard(iCityID)
				else:
					self.selectedCityIDs.add(iCityID)
				self.updateCheckboxCell(inputClass.getMouseY(), iCityID, iCityID in self.selectedCityIDs)
		elif ( inputClass.getNotifyCode() == NotifyCode.NOTIFY_CLICKED ):
			szName = inputClass.getFunctionName()
			if (szName == "ConstructionPlannerSelectAll"):
				self.selectAllCities()
			elif (szName == "ConstructionPlannerResetAll"):
				self.resetAllCities()
			elif (szName == "ConstructionPlannerBuildNow"):
				self.applyBuildOrder(False, False)
			elif (szName == "ConstructionPlannerQueueEnd"):
				self.applyBuildOrder(True, False)
			elif (szName == "ConstructionPlannerQueueFront"):
				self.applyBuildOrder(False, True)
			elif (szName == "ConstructionPlannerBuildScrollUp"):
				self.scrollBuildingList(-1)
			elif (szName == "ConstructionPlannerBuildScrollDown"):
				self.scrollBuildingList(1)
			elif (szName.startswith("ConstructionPlannerBuildIcon") or szName.startswith("ConstructionPlannerBuildName")):
				eBuilding = inputClass.getData1()
				if (eBuilding != -1):
					self.selectBuilding(eBuilding)

		return 0

	def update(self, fDelta):
		return
