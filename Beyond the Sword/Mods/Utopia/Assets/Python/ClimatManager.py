from CvPythonExtensions import *
import CvUtil

gc = CyGlobalContext()

# ---- Параметры баланса климатического клеточного автомата ----
CLIMATE_TILES_PER_TURN_MIN = 30        # минимум случайных клеток суши, проверяемых за ход
CLIMATE_TILES_PER_TURN_MAX = 70        # максимум случайных клеток суши, проверяемых за ход
CLIMATE_GREEN_WATER_THRESHOLD = 2      # сколько источников воды рядом нужно, чтобы клетка могла зазеленеть
CLIMATE_GREEN_CHANCE_PER_SOURCE_PERCENT = 3  # % за каждый источник воды (итог = это * кол-во источников)
CLIMATE_DESERT_CHANCE_PERCENT = 15     # плоский шанс (%) опустынивания/заморозки, если условие выполнено
CLIMATE_DESERT_LATITUDE = 65           # |широта| меньше этого - равнина без воды сохнет в пустыню, иначе в тундру
CLIMATE_MIN_LAND_NEIGHBORS = 4         # меньше соседей-суши - клетка на одиноком острове, опустыниваться не может
CLIMATE_FOREST_SPREAD_CHANCE_PERCENT = 2  # % за каждого подходящего соседа с лесом (итог = это * кол-во соседей)
CLIMATE_JUNGLE_SPREAD_CHANCE_PERCENT = 3  # % за каждого подходящего соседа с джунглями

# Улучшения, при которых клетка точно не может зазеленеть (но может опустыниться)
CLIMATE_NEVER_GREEN_IMPROVEMENTS = [
    "IMPROVEMENT_CITY_RUINS",
    "IMPROVEMENT_CITY_RUINS_ARCOLOGY",
    "IMPROVEMENT_MINE",
    "IMPROVEMENT_EXTRACTION_FACILITY",
    "IMPROVEMENT_WORKSHOP",
    "IMPROVEMENT_QUARRY",
    "IMPROVEMENT_GLASSBLOWING",
    "IMPROVEMENT_WELL",
    "IMPROVEMENT_VILLAGE",
    "IMPROVEMENT_TOWN",
]

# Кэш индексов клеток суши - считается один раз за сессию (initLandPlotsCache,
# вызывается из onGameStart/onLoadGame), чтобы не промахиваться по воде каждый раз.
_landPlotIndices = []

def initLandPlotsCache():
    global _landPlotIndices
    mapObj = CyMap()
    totalPlots = mapObj.numPlots()
    iOasis = gc.getInfoTypeForString("FEATURE_OASIS")

    _landPlotIndices = []
    for i in range(totalPlots):
        plot = mapObj.plotByIndex(i)
        if plot.isWater():
            continue
        if plot.isPeak():
            continue  # горы - террейн под ними климат не меняет, нет смысла проверять
        if plot.getFeatureType() == iOasis:
            continue  # оазис - feature, которая никогда не меняется климатом
        _landPlotIndices.append(i)

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
    bodyText += u"</font>"

    popup.setBodyString(bodyText, CvUtil.FONT_LEFT_JUSTIFY)
    popup.addButton("Close")
    popup.launch(False, PopupStates.POPUPSTATE_IMMEDIATE)

    CvUtil.pyPrint('ClimateManager: Full analytics popup displayed successfully.')
    
def _aridityTier(terrain, iPlains, iDesert, iTundra, iSnow):
    # Шкала "зелёности" для сравнения террейнов: 0 - самый зелёный (луга и всё
    # остальное, что не входит в цепочку), дальше суше/холоднее по возрастанию.
    if terrain == iSnow:
        return 3
    if terrain == iDesert or terrain == iTundra:
        return 2
    if terrain == iPlains:
        return 1
    return 0

def _scanNeighbors(plot, iOwnTerrain, iOwnTier, iForest, iJungle, iForestPreserve, iPlains, iDesert, iTundra, iSnow):
    # Один проход по 8 соседям считает:
    # - сушу (защита одиноких островов от опустынивания);
    # - источники воды (гора/река/лес-джунгли, лес+заповедник = 2) - независимые,
    #   складываются с одной и той же клетки-соседа;
    # - самый "сухой" уровень среди соседей-суши (граница, выше которой клетка
    #   не опустынится за один проход, даже если условие выполнено);
    # - соседей с лесом/джунглями того же террейна ИЛИ террейна суше/холоднее
    #   нашего (для распространения растительности на лучшую почву).
    iLandCount = 0
    iWaterSources = 0
    iMaxNeighborTier = -1
    iMatchingForestCount = 0
    iMatchingJungleCount = 0
    iX = plot.getX()
    iY = plot.getY()
    for iDX in range(-1, 2):
        for iDY in range(-1, 2):
            if iDX == 0 and iDY == 0:
                continue
            neighborPlot = plotXY(iX, iY, iDX, iDY)
            if not neighborPlot or neighborPlot.isNone():
                continue

            feature = neighborPlot.getFeatureType()
            bHasForest = (feature == iForest)
            bHasJungle = (feature == iJungle)

            if neighborPlot.isPeak():
                iWaterSources += 1
            if neighborPlot.isRiver():
                iWaterSources += 1
            if bHasForest or bHasJungle:
                iWaterSources += 1
                if neighborPlot.getImprovementType() == iForestPreserve:
                    iWaterSources += 1

            if neighborPlot.isWater():
                continue

            iLandCount += 1

            if neighborPlot.isPeak():
                continue  # гора не входит в цепочку террейнов - не считаем её "уровень"

            neighborTerrain = neighborPlot.getTerrainType()
            iNeighborTier = _aridityTier(neighborTerrain, iPlains, iDesert, iTundra, iSnow)
            if iNeighborTier > iMaxNeighborTier:
                iMaxNeighborTier = iNeighborTier

            if neighborTerrain == iOwnTerrain or iNeighborTier > iOwnTier:
                if bHasForest:
                    iMatchingForestCount += 1
                elif bHasJungle:
                    iMatchingJungleCount += 1

    return (iLandCount, iWaterSources, iMaxNeighborTier, iMatchingForestCount, iMatchingJungleCount)

def _pickRandomLandPlot(mapObj):
    # SorenRand - синхронный РНГ движка, одинаковый у всех клиентов в мультиплеере.
    # Обычный Python random() тут недопустим - приведёт к рассинхрону карты.
    # Берём индекс только из кэша суши - промахов по воде больше нет.
    if len(_landPlotIndices) == 0:
        return None
    iIndex = _landPlotIndices[gc.getGame().getSorenRandNum(len(_landPlotIndices), "Climate: pick random land plot")]
    return mapObj.plotByIndex(iIndex)

def processClimateShift():
    mapObj = CyMap()
    if len(_landPlotIndices) == 0:
        return

    iForest = gc.getInfoTypeForString("FEATURE_FOREST")
    iJungle = gc.getInfoTypeForString("FEATURE_JUNGLE")
    iFloodPlains = gc.getInfoTypeForString("FEATURE_FLOOD_PLAINS")
    iForestPreserve = gc.getInfoTypeForString("IMPROVEMENT_FOREST_PRESERVE")
    iDesert = gc.getInfoTypeForString("TERRAIN_DESERT")
    iPlains = gc.getInfoTypeForString("TERRAIN_PLAINS")
    iGrass = gc.getInfoTypeForString("TERRAIN_GRASS")
    iTundra = gc.getInfoTypeForString("TERRAIN_TUNDRA")
    iSnow = gc.getInfoTypeForString("TERRAIN_SNOW")

    listNeverGreenImprovements = [gc.getInfoTypeForString(szType) for szType in CLIMATE_NEVER_GREEN_IMPROVEMENTS]

    iRange = CLIMATE_TILES_PER_TURN_MAX - CLIMATE_TILES_PER_TURN_MIN
    iTilesThisTurn = CLIMATE_TILES_PER_TURN_MIN + gc.getGame().getSorenRandNum(iRange + 1, "Climate: tiles to check this turn")

    for i in range(iTilesThisTurn):
        plot = _pickRandomLandPlot(mapObj)
        if plot is None:
            continue

        feature = plot.getFeatureType()

        # Пойму и полноценный город (не городок-улучшение) климат не трогает вообще
        if feature == iFloodPlains or plot.isCity():
            continue

        terrain = plot.getTerrainType()
        iOwnTier = _aridityTier(terrain, iPlains, iDesert, iTundra, iSnow)
        bHasVegetation = (feature == iForest or feature == iJungle)
        bBlockedFromGreening = plot.getImprovementType() in listNeverGreenImprovements

        (iLandNeighbors, iWaterSources, iMaxNeighborTier,
         iMatchingForestNeighbors, iMatchingJungleNeighbors) = _scanNeighbors(
            plot, terrain, iOwnTier, iForest, iJungle, iForestPreserve, iPlains, iDesert, iTundra, iSnow)

        # Лес/джунгли на клетке - защита от опустынивания (но не от озеленения).
        # Остров (< CLIMATE_MIN_LAND_NEIGHBORS соседей-суши) - та же защита.
        bCanDesertify = (not bHasVegetation) and (iLandNeighbors >= CLIMATE_MIN_LAND_NEIGHBORS)
        bCanGreen = not bBlockedFromGreening

        iNewTerrain = -1

        if bCanDesertify and iWaterSources == 0:
            # Источников воды рядом нет вообще - клетка сохнет/мёрзнет на шаг,
            # но не дальше уровня самого "сухого" соседа рядом (без скачков в никуда).
            iTargetTerrain = -1
            iTargetTier = -1
            if terrain == iGrass:
                iTargetTerrain = iPlains
                iTargetTier = 1
            elif terrain == iPlains:
                if abs(plot.getLatitude()) < CLIMATE_DESERT_LATITUDE:
                    iTargetTerrain = iDesert
                else:
                    iTargetTerrain = iTundra
                iTargetTier = 2
            elif terrain == iTundra:
                iTargetTerrain = iSnow
                iTargetTier = 3

            if iTargetTerrain != -1 and iMaxNeighborTier >= iTargetTier:
                if gc.getGame().getSorenRandNum(100, "Climate: desertify roll") < CLIMATE_DESERT_CHANCE_PERCENT:
                    iNewTerrain = iTargetTerrain

        elif bCanGreen and iWaterSources >= CLIMATE_GREEN_WATER_THRESHOLD:
            # Источников воды рядом достаточно - клетка зеленеет на шаг.
            # Шанс растёт с количеством источников (каждый добавляет свой %).
            iTargetTerrain = -1
            if terrain == iDesert:
                iTargetTerrain = iPlains
            elif terrain == iPlains:
                iTargetTerrain = iGrass
            elif terrain == iSnow:
                iTargetTerrain = iTundra
            elif terrain == iTundra:
                iTargetTerrain = iPlains

            if iTargetTerrain != -1:
                iChance = iWaterSources * CLIMATE_GREEN_CHANCE_PER_SOURCE_PERCENT
                if gc.getGame().getSorenRandNum(100, "Climate: green roll") < iChance:
                    iNewTerrain = iTargetTerrain

        if iNewTerrain != -1:
            plot.setTerrainType(iNewTerrain, True, True) # True аргументы обновляют графику и карту
            continue  # смена террейна - растительность на эту клетку в этот проход не распространяем

        # Распространение растительности - только на клетку без feature (пойма/
        # город уже отфильтрованы выше, лес/джунгли сюда просто не доходят, т.к.
        # terrain-переход выше уже случился бы раньше через continue).
        if feature != FeatureTypes.NO_FEATURE:
            continue

        # Лес/джунгли могут "перепрыгнуть" на соседнюю клетку того же террейна ИЛИ
        # террейна суше/холоднее нашего (переселяются на почву не хуже своей).
        # Шанс = базовый % * количество таких соседей, лес и джунгли - отдельно.
        if iMatchingForestNeighbors > 0:
            iForestChance = CLIMATE_FOREST_SPREAD_CHANCE_PERCENT * iMatchingForestNeighbors
            if gc.getGame().getSorenRandNum(100, "Climate: forest spread roll") < iForestChance:
                plot.setFeatureType(iForest, -1)
                continue

        if iMatchingJungleNeighbors > 0:
            iJungleChance = CLIMATE_JUNGLE_SPREAD_CHANCE_PERCENT * iMatchingJungleNeighbors
            if gc.getGame().getSorenRandNum(100, "Climate: jungle spread roll") < iJungleChance:
                plot.setFeatureType(iJungle, -1)