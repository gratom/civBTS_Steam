from CvPythonExtensions import *
import CvUtil
import ModGameData

gc = CyGlobalContext()

# ---- Параметры баланса климатического клеточного автомата ----
CLIMATE_TILES_PER_TURN = 50            # сколько случайных клеток суши проверяем за ход
CLIMATE_SHIFT_CHANCE_PERCENT = 20      # шанс (%), что подходящая клетка реально сменит террейн
CLIMATE_VEGETATION_NEIGHBOR_THRESHOLD = 2  # сколько соседних лесов/джунглей считается "достаточно" для озеленения
CLIMATE_DESERT_LATITUDE = 65           # |широта| меньше этого - равнина без леса сохнет в пустыню, иначе в тундру
CLIMATE_MIN_LAND_NEIGHBORS = 3         # меньше соседей-суши - клетка на одиноком острове, климат не трогаем
CLIMATE_SPREAD_NEIGHBOR_THRESHOLD = 2  # дальше равнины (пустыня/тундра/лёд) ползёт только от уже готовых соседей такого же типа
CLIMATE_LAND_PICK_ATTEMPTS = 8         # попыток найти клетку суши на один слот (техническая настройка, не баланс)
CLIMATE_FOREST_SPREAD_CHANCE_PERCENT = 2  # % за каждого соседа того же террейна с лесом (итог = это * кол-во соседей)
CLIMATE_JUNGLE_SPREAD_CHANCE_PERCENT = 3  # % за каждого соседа того же террейна с джунглями

# Global state memory
climateData = {}

def saveClimateData():
    global climateData
    ModGameData.updateValues({
        "temperature": climateData.get("temperature", 0),
        "pollution": climateData.get("pollution", 100),
    })

def loadClimateData():
    global climateData
    data = ModGameData.loadAll()
    climateData = {
        "temperature": data.get("temperature", 0),
        "pollution": data.get("pollution", 100),
    }

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
    
def _scanNeighbors(plot, iOwnTerrain, iForest, iJungle, iDesert, iTundra, iSnow):
    # Один проход по 8 соседям сразу считает сушу, растительность (лес/джунгли),
    # уже существующие "заразные" террейны (пустыня/тундра/лёд) и соседей с лесом/
    # джунглями ТОГО ЖЕ террейна, что и наша клетка (для распространения растительности).
    iLandCount = 0
    iVegCount = 0
    iDesertCount = 0
    iTundraCount = 0
    iSnowCount = 0
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
            if neighborPlot.isWater():
                continue
            iLandCount += 1
            feature = neighborPlot.getFeatureType()
            if feature == iForest or feature == iJungle:
                iVegCount += 1
            neighborTerrain = neighborPlot.getTerrainType()
            if neighborTerrain == iDesert:
                iDesertCount += 1
            elif neighborTerrain == iTundra:
                iTundraCount += 1
            elif neighborTerrain == iSnow:
                iSnowCount += 1
            if neighborTerrain == iOwnTerrain:
                if feature == iForest:
                    iMatchingForestCount += 1
                elif feature == iJungle:
                    iMatchingJungleCount += 1
    return (iLandCount, iVegCount, iDesertCount, iTundraCount, iSnowCount, iMatchingForestCount, iMatchingJungleCount)

def _pickRandomLandPlot(mapObj, totalPlots):
    # SorenRand - синхронный РНГ движка, одинаковый у всех клиентов в мультиплеере.
    # Обычный Python random() тут недопустим - приведёт к рассинхрону карты.
    for i in range(CLIMATE_LAND_PICK_ATTEMPTS):
        iIndex = gc.getGame().getSorenRandNum(totalPlots, "Climate: pick random plot")
        plot = mapObj.plotByIndex(iIndex)
        if not plot.isWater():
            return plot
    return None

def processClimateShift():
    mapObj = CyMap()
    totalPlots = mapObj.numPlots()
    if totalPlots == 0:
        return

    iForest = gc.getInfoTypeForString("FEATURE_FOREST")
    iJungle = gc.getInfoTypeForString("FEATURE_JUNGLE")
    iDesert = gc.getInfoTypeForString("TERRAIN_DESERT")
    iPlains = gc.getInfoTypeForString("TERRAIN_PLAINS")
    iGrass = gc.getInfoTypeForString("TERRAIN_GRASS")
    iTundra = gc.getInfoTypeForString("TERRAIN_TUNDRA")
    iSnow = gc.getInfoTypeForString("TERRAIN_SNOW")

    for i in range(CLIMATE_TILES_PER_TURN):
        plot = _pickRandomLandPlot(mapObj, totalPlots)
        if plot is None:
            continue

        # Лес/джунгли (или оазис/т.п.) на самой клетке "консервируют" её террейн
        if plot.getFeatureType() != FeatureTypes.NO_FEATURE:
            continue

        terrain = plot.getTerrainType()
        (iLandNeighbors, iVegNeighbors, iDesertNeighbors, iTundraNeighbors, iSnowNeighbors,
         iMatchingForestNeighbors, iMatchingJungleNeighbors) = _scanNeighbors(plot, terrain, iForest, iJungle, iDesert, iTundra, iSnow)
        if iLandNeighbors < CLIMATE_MIN_LAND_NEIGHBORS:
            continue  # одинокий остров - климат его не трогает

        iNewTerrain = -1

        if iVegNeighbors >= CLIMATE_VEGETATION_NEIGHBOR_THRESHOLD:
            # Лес/джунгли рядом - клетка "зеленеет"
            if terrain == iDesert:
                iNewTerrain = iPlains
            elif terrain == iPlains:
                iNewTerrain = iGrass
            elif terrain == iSnow:
                iNewTerrain = iTundra
            elif terrain == iTundra:
                iNewTerrain = iPlains
        elif iVegNeighbors == 0:
            # Растительности рядом нет - клетка деградирует.
            # До равнины опустынивание/заморозка идёт свободно, а дальше (в пустыню,
            # тундру или лёд) - только если рядом уже есть минимум 2 таких соседа,
            # иначе это выглядело бы как пустыня/тундра/лёд "из ниоткуда".
            if terrain == iGrass:
                iNewTerrain = iPlains
            elif terrain == iPlains:
                if abs(plot.getLatitude()) < CLIMATE_DESERT_LATITUDE:
                    if iDesertNeighbors >= CLIMATE_SPREAD_NEIGHBOR_THRESHOLD:
                        iNewTerrain = iDesert
                else:
                    if iTundraNeighbors >= CLIMATE_SPREAD_NEIGHBOR_THRESHOLD:
                        iNewTerrain = iTundra
            elif terrain == iTundra:
                if iSnowNeighbors >= CLIMATE_SPREAD_NEIGHBOR_THRESHOLD:
                    iNewTerrain = iSnow

        if iNewTerrain != -1 and iNewTerrain != terrain:
            if gc.getGame().getSorenRandNum(100, "Climate: terrain shift roll") < CLIMATE_SHIFT_CHANCE_PERCENT:
                plot.setTerrainType(iNewTerrain, True, True) # True аргументы обновляют графику и карту
                continue  # смена террейна - растительность на эту клетку в этот проход не распространяем

        # Распространение растительности: лес/джунгли могут "перепрыгнуть" на соседнюю
        # клетку ТОГО ЖЕ террейна (тундра рядом с тундрой, равнина рядом с равниной и т.д.).
        # Шанс = базовый % * количество таких соседей, лес и джунгли считаются отдельно.
        if iMatchingForestNeighbors > 0:
            iForestChance = CLIMATE_FOREST_SPREAD_CHANCE_PERCENT * iMatchingForestNeighbors
            if gc.getGame().getSorenRandNum(100, "Climate: forest spread roll") < iForestChance:
                plot.setFeatureType(iForest, -1)
                continue

        if iMatchingJungleNeighbors > 0:
            iJungleChance = CLIMATE_JUNGLE_SPREAD_CHANCE_PERCENT * iMatchingJungleNeighbors
            if gc.getGame().getSorenRandNum(100, "Climate: jungle spread roll") < iJungleChance:
                plot.setFeatureType(iJungle, -1)