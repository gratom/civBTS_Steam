from CvPythonExtensions import *
import CvUtil

gc = CyGlobalContext()

def showClimatePopup():
    # --- Считаем леса и общую площадь карты ---
    mapObj = CyMap()
    totalPlots = mapObj.numPlots()
    forestCount = 0
    jungleCount = 0

    # Получаем ID фичей леса и джунглей через глобальный контекст
    iForest = gc.getInfoTypeForString("FEATURE_FOREST")
    iJungle = gc.getInfoTypeForString("FEATURE_JUNGLE")

    # Пробегаем по всем тайлам карты
    for i in range(totalPlots):
        plot = mapObj.plotByIndex(i)
        if not plot.isWater(): # Нас интересует только суша
            feature = plot.getFeatureType()
            if feature == iForest:
                forestCount += 1
            elif feature == iJungle:
                jungleCount += 1

    # Пока что заглушка для загрязнений, но леса и джунгли берем честно с карты
    pollution = 120
    absorption = (forestCount + jungleCount) * 2  # Условный коэффициент поглощения
    netBalance = pollution - absorption

    # --- Формируем текст для окна ---
    popup = CyPopup(777, EventContextTypes.EVENTCONTEXT_SELF, True)
    popup.setHeaderString("Global Climate Status", CvUtil.FONT_CENTER_JUSTIFY)

    bodyText = u"<font=3>Current Climate Balance:\n\n"
    bodyText += u"- Forests on Map: %d\n" % forestCount
    bodyText += u"- Jungles on Map: %d\n" % jungleCount
    bodyText += u"- Total Pollution (Buildings + Nukes): +%d\n" % pollution
    bodyText += u"- Total Absorption: -%d\n" % absorption

    if netBalance > 0:
        bodyText += u"- Net Balance: +%d (Warming)</font>" % netBalance
    else:
        bodyText += u"- Net Balance: %d (Cooling / Ice Age)</font>" % netBalance

    popup.setBodyString(bodyText, CvUtil.FONT_LEFT_JUSTIFY)
    popup.addButton("Close")
    popup.launch(False, PopupStates.POPUPSTATE_IMMEDIATE)

def processDesertGreening():
    mapObj = CyMap()
    totalPlots = mapObj.numPlots()

    # Получаем ID типов местности через глобальный контекст
    iDesert = gc.getInfoTypeForString("TERRAIN_DESERT")
    iPlains = gc.getInfoTypeForString("TERRAIN_PLAINS")
    iGrass = gc.getInfoTypeForString("TERRAIN_GRASS")

    changedCount = 0

    # Пробегаем по всем тайлам карты
    for i in range(totalPlots):
        plot = mapObj.plotByIndex(i)

        # Проверяем, что это суша и что это пустыня
        if not plot.isWater() and plot.getTerrainType() == iDesert:

            # Допустим, превращаем пустыню в равнину
            plot.setTerrainType(iPlains, True, True) # True аргументы обновляют графику и карту
            changedCount += 1

            # Пример ограничения: если хотим озеленить только первые 10 тайлов для теста
            if changedCount >= 10: break