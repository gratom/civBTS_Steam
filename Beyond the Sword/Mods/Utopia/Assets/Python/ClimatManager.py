from CvPythonExtensions import *
import CvUtil
import cPickle as pickle # В Python 2.4 (на котором работает Civ 4) используется cPickle

gc = CyGlobalContext()

# Global state memory
climateData = {}

def saveClimateData():
    global climateData
    dataString = pickle.dumps(climateData)
    CyGame().setScriptData(dataString)

def loadClimateData():
    global climateData
    dataString = CyGame().getScriptData()
    if dataString == "":
        climateData = {"temperature": 0, "pollution": 100}
    else:
        climateData = pickle.loads(dataString)

def showClimatePopup():
    CvUtil.pyPrint('ClimateManager: popup called')

    mapObj = CyMap()
    totalPlots = mapObj.numPlots()

    # Счетчики
    landCount = 0
    waterCount = 0

    forestCount = 0
    jungleCount = 0
    iceFeatureCount = 0

    desertCount = 0
    plainsCount = 0
    grassCount = 0
    tundraCount = 0
    snowTerrainCount = 0

    # Получаем ID через глобальный контекст
    iForest = gc.getInfoTypeForString("FEATURE_FOREST")
    iJungle = gc.getInfoTypeForString("FEATURE_JUNGLE")
    iIceFeature = gc.getInfoTypeForString("FEATURE_ICE")

    iDesert = gc.getInfoTypeForString("TERRAIN_DESERT")
    iPlains = gc.getInfoTypeForString("TERRAIN_PLAINS")
    iGrass = gc.getInfoTypeForString("TERRAIN_GRASS")
    iTundraTerrain = gc.getInfoTypeForString("TERRAIN_TUNDRA")
    iSnowTerrain = gc.getInfoTypeForString("TERRAIN_SNOW")

    # Пробегаем по всем тайлам карты
    for i in range(totalPlots):
        plot = mapObj.plotByIndex(i)

        # Вода / Суша
        if plot.isWater():
            waterCount += 1
        else:
            landCount += 1

            # Типы террейна суши
            terrain = plot.getTerrainType()
            if terrain == iDesert:
                desertCount += 1
            elif terrain == iPlains:
                plainsCount += 1
            elif terrain == iGrass:
                grassCount += 1
            elif terrain == iTundraTerrain:
                tundraCount += 1
            elif terrain == iSnowTerrain:
                snowTerrainCount += 1

        # Фичи на тайлах
        feature = plot.getFeatureType()
        if feature == iForest:
            forestCount += 1
        elif feature == iJungle:
            jungleCount += 1
        elif feature == iIceFeature:
            iceFeatureCount += 1

    # Защита от деления на ноль
    if totalPlots == 0: totalPlots = 1
    if landCount == 0: landCount = 1

    # Расчет процентов от суши
    landPercent = (float(landCount) / totalPlots) * 100.0
    waterPercent = (float(waterCount) / totalPlots) * 100.0

    forestPercent = (float(forestCount) / landCount) * 100.0
    junglePercent = (float(jungleCount) / landCount) * 100.0
    icePercent = (float(iceFeatureCount) / landCount) * 100.0

    desertPercent = (float(desertCount) / landCount) * 100.0
    plainsPercent = (float(plainsCount) / landCount) * 100.0
    grassPercent = (float(grassCount) / landCount) * 100.0
    tundraPercent = (float(tundraCount) / landCount) * 100.0
    snowPercent = (float(snowTerrainCount) / landCount) * 100.0

    # Условные расчеты баланса
    pollution = 120
    absorption = (forestCount + jungleCount) * 2
    netBalance = pollution - absorption

    # --- Формируем текст для окна ---
    popup = CyPopup(777, EventContextTypes.EVENTCONTEXT_SELF, True)
    popup.setHeaderString("Global Climate & Map Analytics", CvUtil.FONT_CENTER_JUSTIFY)

    bodyText = u"<font=2>"
    bodyText += u"<b>--- WORLD PROPORTIONS ---</b>\n"
    bodyText += u"- Total Land: %d (%.1f%% of world)\n" % (landCount, landPercent)
    bodyText += u"- Total Water: %d (%.1f%% of world)\n\n" % (waterCount, waterPercent)

    bodyText += u"<b>--- TERRAIN BREAKDOWN (100% of Land) ---</b>\n"
    bodyText += u"- Deserts: %d (%.1f%%)\n" % (desertCount, desertPercent)
    bodyText += u"- Plains: %d (%.1f%%)\n" % (plainsCount, plainsPercent)
    bodyText += u"- Grasslands: %d (%.1f%%)\n" % (grassCount, grassPercent)
    bodyText += u"- Tundra: %d (%.1f%%)\n" % (tundraCount, tundraPercent)
    bodyText += u"- Snow: %d (%.1f%%)\n\n" % (snowTerrainCount, snowPercent)

    bodyText += u"<b>--- FEATURES (% of Land) ---</b>\n"
    bodyText += u"- Forests: %d (%.1f%%)\n" % (forestCount, forestPercent)
    bodyText += u"- Jungles: %d (%.1f%%)\n" % (jungleCount, junglePercent)
    bodyText += u"- Ice (Features): %d (%.1f%%)\n\n" % (iceFeatureCount, icePercent)

    bodyText += u"<b>--- CLIMATE BALANCE ---</b>\n"
    bodyText += u"- Pollution: +%d | Absorption: -%d\n" % (pollution, absorption)

    if netBalance > 0:
        bodyText += u"- Net Balance: +%d <color=249,125,125>(Warming)</color>" % netBalance
    else:
        bodyText += u"- Net Balance: %d <color=125,249,125>(Cooling)</color>" % netBalance

    bodyText += u"</font>"

    popup.setBodyString(bodyText, CvUtil.FONT_LEFT_JUSTIFY)
    popup.addButton("Close")
    popup.launch(False, PopupStates.POPUPSTATE_IMMEDIATE)

    CvUtil.pyPrint('ClimateManager: Full analytics popup displayed successfully.')
    
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