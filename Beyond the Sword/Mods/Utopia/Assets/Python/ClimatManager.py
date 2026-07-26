from CvPythonExtensions import *
import CvUtil

def processGlobalClimate():
    CvUtil.pyPrint('ClimateManager: processGlobalClimate called')
    
def showClimatePopup():
    # Создаем всплывающее окно с уникальным ID (например, 777)
    CvUtil.pyPrint('ClimateManager: popup called')
    popup = CyPopup(777, EventContextTypes.EVENTCONTEXT_SELF, True)
    
    # Заголовок окна
    popup.setHeaderString("Global Climate Status", CvUtil.FONT_CENTER_JUSTIFY)
    
    # Текст внутри окна (здесь потом подставим наши переменные расчета)
    bodyText = u"<font=3>Current Climate Balance:\n\n"
    bodyText += u"- Total Pollution (Buildings + Nukes): +120\n"
    bodyText += u"- Total Absorption (Forests & Jungles): -85\n"
    bodyText += u"- Net Balance: +35 (Warming)</font>"
    
    popup.setBodyString(bodyText, CvUtil.FONT_LEFT_JUSTIFY)
    
    # Добавляем кнопку закрытия
    popup.addButton("Close")
    
    # Показываем окно игроку (True означает модальное окно, блокирующее игру до закрытия)
    popup.launch(False, PopupStates.POPUPSTATE_IMMEDIATE)
    CvUtil.pyPrint('ClimateManager: popup SHOWED')