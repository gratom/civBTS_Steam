## Utopia mod - Construction Planner
## Lets the player pick a subset of cities and a regular building, then push that
## building onto all of them at once (build now / queue at end / queue at front).
##
## The city list is a real GFC table. The building list is a real addScrollPanel -
## the same native scrollable-content widget CvTechChooser uses for the tech tree
## (screen.addScrollPanel + attachPanelAt/setTextAt/addDDSGFCAt + setViewMin) - so it
## gets a proper draggable scrollbar for free, no manual offset/arrow bookkeeping.
## Running two addTableControlGFC tables in the same screen turned out unreliable,
## so the building list deliberately avoids a second Table and uses this instead.
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

BUILD_PANEL_NAME = "ConstructionPlannerBuildScroll"
BUILD_ROW_HEIGHT = 36
BUILD_ICON_SIZE = 32
BUILD_NAME_WIDTH = 185
BUILD_COST_WIDTH = 85
BUILD_GAP = 8

class CvConstructionPlanner:
	"Construction Planner Screen"
	def __init__(self):
		self.selectedCityIDs = set()
		self.selectedBuildingType = -1
		self.buildableBuildings = []
		self.iActivePlayer = -1

	# Screen construction function
	def interfaceScreen(self):
		screen = CyGInterfaceScreen( SCREEN_NAME, CvScreenEnums.CONSTRUCTION_PLANNER )

		self.iActivePlayer = gc.getGame().getActivePlayer()
		self.buildableBuildings = self.computeBuildableBuildings()

		self.nListX = 20
		self.nListWidth = 330
		self.nListY = 119

		self.nBuildX = self.nListX + self.nListWidth + 24
		self.nBuildWidth = BUILD_ICON_SIZE + BUILD_GAP + BUILD_NAME_WIDTH + BUILD_GAP + BUILD_COST_WIDTH

		self.nScreenWidth = self.nBuildX + self.nBuildWidth + 20
		self.nScreenHeight = 644
		self.nListHeight = self.nScreenHeight - self.nListY - 60

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

		# Build-order action buttons - 2x2 grid above the building list
		iActionWidth = (self.nBuildWidth - 8) / 2
		screen.setButtonGFC( "ConstructionPlannerBuildNow", localText.getText("TXT_KEY_UTOPIA_BUILD_NOW", ()), "", self.nBuildX, 55, iActionWidth, 26, WidgetTypes.WIDGET_GENERAL, -1, -1, ButtonStyles.BUTTON_STYLE_STANDARD )
		screen.setButtonGFC( "ConstructionPlannerQueueEnd", localText.getText("TXT_KEY_UTOPIA_QUEUE_AT_END", ()), "", self.nBuildX + iActionWidth + 8, 55, iActionWidth, 26, WidgetTypes.WIDGET_GENERAL, -1, -1, ButtonStyles.BUTTON_STYLE_STANDARD )
		screen.setButtonGFC( "ConstructionPlannerQueueFront", localText.getText("TXT_KEY_UTOPIA_QUEUE_AT_FRONT", ()), "", self.nBuildX, 85, iActionWidth, 26, WidgetTypes.WIDGET_GENERAL, -1, -1, ButtonStyles.BUTTON_STYLE_STANDARD )
		screen.setButtonGFC( "ConstructionPlannerRemoveFromQueue", localText.getText("TXT_KEY_UTOPIA_REMOVE_FROM_QUEUE", ()), "", self.nBuildX + iActionWidth + 8, 85, iActionWidth, 26, WidgetTypes.WIDGET_GENERAL, -1, -1, ButtonStyles.BUTTON_STYLE_STANDARD )

		# Building list - a real scroll panel (same widget CvTechChooser uses for the tech
		# tree), so it gets a proper native scrollbar instead of our own arrow buttons.
		screen.addScrollPanel( BUILD_PANEL_NAME, u"", self.nBuildX, self.nListY, self.nBuildWidth, self.nListHeight, PanelStyles.PANEL_STYLE_EXTERNAL )
		screen.setViewMin( BUILD_PANEL_NAME, self.nBuildWidth, max(self.nListHeight, len(self.buildableBuildings) * BUILD_ROW_HEIGHT) )
		screen.show( BUILD_PANEL_NAME )

		# Close button, bottom right - same style as the other advisor screens
		screen.setText( "ConstructionPlannerClose", "Background", localText.getText("TXT_KEY_PEDIA_SCREEN_EXIT", ()).upper(), CvUtil.FONT_RIGHT_JUSTIFY, self.nScreenWidth - 25, self.nScreenHeight - 35, -0.1, FontTypes.TITLE_FONT, WidgetTypes.WIDGET_CLOSE_SCREEN, -1, -1 )

		self.drawCityList()
		self.drawBuildingList()

	def getRowIconName(self, i):
		return "ConstructionPlannerBuildIcon" + str(i)

	def getRowNameName(self, i):
		return "ConstructionPlannerBuildName" + str(i)

	def getRowCostName(self, i):
		return "ConstructionPlannerBuildCost" + str(i)

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

	# Builds every building row once, all at once, inside the scroll panel's content
	# space (coordinates here are relative to the panel's content, not the screen -
	# row i sits at y = i * BUILD_ROW_HEIGHT regardless of how tall the panel itself is).
	def drawBuildingList(self):
		screen = CyGInterfaceScreen( SCREEN_NAME, CvScreenEnums.CONSTRUCTION_PLANNER )
		szHammerIcon = u"<font=2>" + (u"%c" % gc.getYieldInfo(YieldTypes.YIELD_PRODUCTION).getChar()) + u"</font>"
		player = gc.getPlayer(self.iActivePlayer)

		i = 0
		for eBuilding in self.buildableBuildings:
			pBuildingInfo = gc.getBuildingInfo(eBuilding)
			iRowY = i * BUILD_ROW_HEIGHT

			screen.addDDSGFCAt( self.getRowIconName(i), BUILD_PANEL_NAME, pBuildingInfo.getButton(), 0, iRowY, BUILD_ICON_SIZE, BUILD_ICON_SIZE, WidgetTypes.WIDGET_GENERAL, eBuilding, -1, False )

			szCost = unicode(player.getBuildingProductionNeeded(eBuilding)) + u" " + szHammerIcon
			screen.setLabelAt( self.getRowCostName(i), BUILD_PANEL_NAME, szCost, CvUtil.FONT_RIGHT_JUSTIFY, BUILD_ICON_SIZE + BUILD_GAP + BUILD_NAME_WIDTH + BUILD_GAP, iRowY + 6, -0.1, FontTypes.SMALL_FONT, WidgetTypes.WIDGET_GENERAL, -1, -1 )

			self.updateBuildingNameRow(i, eBuilding)
			i += 1

	def updateBuildingNameRow(self, i, eBuilding):
		screen = CyGInterfaceScreen( SCREEN_NAME, CvScreenEnums.CONSTRUCTION_PLANNER )
		szName = gc.getBuildingInfo(eBuilding).getDescription()
		if (eBuilding == self.selectedBuildingType):
			szName = localText.getText("TXT_KEY_COLOR_POSITIVE", ()) + szName + localText.getText("TXT_KEY_COLOR_REVERT", ())
		screen.setTextAt( self.getRowNameName(i), BUILD_PANEL_NAME, szName, CvUtil.FONT_LEFT_JUSTIFY, BUILD_ICON_SIZE + BUILD_GAP, i * BUILD_ROW_HEIGHT + 6, -0.1, FontTypes.SMALL_FONT, WidgetTypes.WIDGET_GENERAL, eBuilding, -1 )

	def selectBuilding(self, eBuilding):
		if (eBuilding == self.selectedBuildingType):
			return
		self.selectedBuildingType = eBuilding

		i = 0
		for eLoopBuilding in self.buildableBuildings:
			self.updateBuildingNameRow(i, eLoopBuilding)
			i += 1

	# Pushes the selected building onto every selected city's order queue.
	# bShift/bCtrl match the real key-held meaning used by the native city screen:
	# neither -> replace current production, bShift -> queue at the end,
	# bCtrl -> insert at the front without dropping whatever was being built.
	def applyBuildOrder(self, bShift, bCtrl):
		if (self.selectedBuildingType == -1 or len(self.selectedCityIDs) == 0):
			return
		for iCityID in self.selectedCityIDs:
			CyMessageControl().sendPushOrder(iCityID, OrderTypes.ORDER_CONSTRUCT, self.selectedBuildingType, False, bShift, bCtrl)

	# Removes the selected building from every selected city's queue, wherever it appears.
	# There's no networked "pop this one order" message exposed to Python (CvMessageControl::
	# sendPopOrder exists in the DLL but isn't bound), so this rebuilds the queue instead -
	# read it, clear it (TASK_CLEAR_ORDERS, networked), then re-push everything except the
	# target building, in the same order (sendPushOrder, networked). Net effect is the same
	# as popping that one order, except any shields already accumulated on an in-progress
	# head order being removed are not carried over (same as cancelling it outright).
	def removeBuildingFromQueues(self):
		if (self.selectedBuildingType == -1 or len(self.selectedCityIDs) == 0):
			return
		player = gc.getPlayer(self.iActivePlayer)
		for iCityID in self.selectedCityIDs:
			pCity = player.getCity(iCityID)
			if (not pCity):
				continue

			bFound = False
			remainingOrders = []
			for i in range(pCity.getOrderQueueLength()):
				order = pCity.getOrderFromQueue(i)
				if (order.eOrderType == OrderTypes.ORDER_CONSTRUCT) and (order.iData1 == self.selectedBuildingType):
					bFound = True
					continue
				remainingOrders.append((order.eOrderType, order.iData1))

			if not bFound:
				continue

			CyMessageControl().sendDoTask(iCityID, TaskTypes.TASK_CLEAR_ORDERS, -1, -1, False, False, False, False)
			for (eOrderType, iData1) in remainingOrders:
				CyMessageControl().sendPushOrder(iCityID, eOrderType, iData1, False, True, False)

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
			elif (szName == "ConstructionPlannerRemoveFromQueue"):
				self.removeBuildingFromQueues()
			elif (szName.startswith("ConstructionPlannerBuildIcon") or szName.startswith("ConstructionPlannerBuildName")):
				eBuilding = inputClass.getData1()
				if (eBuilding != -1):
					self.selectBuilding(eBuilding)

		return 0

	def update(self, fDelta):
		return
