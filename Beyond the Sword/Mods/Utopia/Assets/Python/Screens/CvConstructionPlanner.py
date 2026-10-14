## Utopia mod - Construction Planner
## Lets the player pick a subset of cities to later apply a build order to in bulk.
## This window is just the city picker for now - the actual "build this everywhere"
## action will be added on top of it later.
from CvPythonExtensions import *
import CvUtil
import CvScreenEnums

gc = CyGlobalContext()
localText = CyTranslator()

SCREEN_NAME = "ConstructionPlanner"
TABLE_NAME = "ConstructionPlannerCityList"

COLUMN_CHECK = 0
COLUMN_NAME = 1

CHECK_MARK_TEXT = u"[x]"
CHECK_EMPTY_TEXT = u"[ ]"

class CvConstructionPlanner:
	"Construction Planner Screen"
	def __init__(self):
		self.selectedCityIDs = set()
		self.iActivePlayer = -1

	# Screen construction function
	def interfaceScreen(self):
		screen = CyGInterfaceScreen( SCREEN_NAME, CvScreenEnums.CONSTRUCTION_PLANNER )

		self.iActivePlayer = gc.getGame().getActivePlayer()

		# Window is intentionally wider than the city list - the right side is reserved
		# for the build-order controls that will be added on top of this picker later.
		self.nScreenWidth = 760
		self.nScreenHeight = 560

		self.nListX = 20
		self.nListWidth = 280
		self.nListY = 95
		self.nListHeight = self.nScreenHeight - self.nListY - 60

		screen.setRenderInterfaceOnly(True)
		screen.setDimensions(100, 100, self.nScreenWidth, self.nScreenHeight)
		screen.showScreen(PopupStates.POPUPSTATE_IMMEDIATE, False)

		screen.addPanel( "ConstructionPlannerBG", u"", u"", True, False, 0, 0, self.nScreenWidth, self.nScreenHeight, PanelStyles.PANEL_STYLE_MAIN )

		screen.setLabel( "ConstructionPlannerTitle", "Background", localText.getText("TXT_KEY_UTOPIA_CONSTRUCTION_PLANNER", ()), CvUtil.FONT_LEFT_JUSTIFY, self.nListX, 20, -0.1, FontTypes.TITLE_FONT, WidgetTypes.WIDGET_GENERAL, -1, -1 )

		# Select All / Reset All
		iHalfWidth = (self.nListWidth - 8) / 2
		screen.setButtonGFC( "ConstructionPlannerSelectAll", localText.getText("TXT_KEY_UTOPIA_SELECT_ALL_CITIES", ()), "", self.nListX, 55, iHalfWidth, 26, WidgetTypes.WIDGET_GENERAL, -1, -1, ButtonStyles.BUTTON_STYLE_STANDARD )
		screen.setButtonGFC( "ConstructionPlannerResetAll", localText.getText("TXT_KEY_UTOPIA_RESET_ALL_CITIES", ()), "", self.nListX + iHalfWidth + 8, 55, iHalfWidth, 26, WidgetTypes.WIDGET_GENERAL, -1, -1, ButtonStyles.BUTTON_STYLE_STANDARD )

		# City list - checkbox column + name column, click anywhere on a row to toggle it
		screen.addTableControlGFC( TABLE_NAME, 2, self.nListX, self.nListY, self.nListWidth, self.nListHeight, True, False, 24, 24, TableStyles.TABLE_STYLE_STANDARD )
		# Selection highlighting is harmless here - we use it the same way CvDomesticAdvisor
		# does (click -> NOTIFY_LISTBOX_ITEM_SELECTED), it just doubles up with our own [x]/[ ] marker
		screen.enableSelect( TABLE_NAME, True )
		screen.setStyle( TABLE_NAME, "Table_StandardCiv_Style" )
		screen.setTableColumnHeader( TABLE_NAME, COLUMN_CHECK, "", 36 )
		screen.setTableColumnHeader( TABLE_NAME, COLUMN_NAME, localText.getText("TXT_KEY_DOMESTIC_ADVISOR_NAME", ()), self.nListWidth - 36 )

		# Close button, bottom right - same style as the other advisor screens
		screen.setText( "ConstructionPlannerClose", "Background", localText.getText("TXT_KEY_PEDIA_SCREEN_EXIT", ()).upper(), CvUtil.FONT_RIGHT_JUSTIFY, self.nScreenWidth - 25, self.nScreenHeight - 35, -0.1, FontTypes.TITLE_FONT, WidgetTypes.WIDGET_CLOSE_SCREEN, -1, -1 )

		self.drawCityList()

	# Builds the city rows once per screen open - row count doesn't change afterwards,
	# only the checkbox cell content gets refreshed in place.
	def drawCityList(self):
		screen = CyGInterfaceScreen( SCREEN_NAME, CvScreenEnums.CONSTRUCTION_PLANNER )
		player = gc.getPlayer(self.iActivePlayer)

		i = 0
		(pLoopCity, iter) = player.firstCity(false)
		while(pLoopCity):
			screen.appendTableRow( TABLE_NAME )
			self.updateCheckboxCell(i, pLoopCity.getID(), pLoopCity.getID() in self.selectedCityIDs)
			screen.setTableText( TABLE_NAME, COLUMN_NAME, i, pLoopCity.getName(), "", WidgetTypes.WIDGET_GENERAL, self.iActivePlayer, pLoopCity.getID(), CvUtil.FONT_LEFT_JUSTIFY )
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
		screen.setTableText( TABLE_NAME, COLUMN_CHECK, iRow, szCheck, "", WidgetTypes.WIDGET_GENERAL, self.iActivePlayer, iCityID, CvUtil.FONT_CENTER_JUSTIFY )

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

		return 0

	def update(self, fDelta):
		return
