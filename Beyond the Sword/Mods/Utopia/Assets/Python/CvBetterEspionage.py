## Utopia
## "Better Espionage": раз в игровой ход сравниваем накопленные очки шпионажа
## (EspionagePoints, это именно накопленный тотал, а не прирост за ход) каждой
## пары команд, которые уже встретились. Если у одной команды значительный
## перевес в EP против другой - есть шанс открыть одну случайную клетку
## территории соперника, как бонус деревни типа "открыть карту".
##
## Правила (см. обсуждение в чате):
##  - перевес считается в % от EP соперника: (myEP - theirEP) / theirEP * 100
##  - количество бросков = (перевес // ADVANTAGE_PERCENT_PER_ROLL) - ADVANTAGE_ROLLS_OFFSET,
##    т.е. с текущими константами (10 и 2) первый бросок появляется только при
##    перевесе >= 30%, дальше +1 бросок за каждые следующие 10% (30%->1, 40%->2,
##    50%->3, 60%->4, ...). При перевесе < 30% бросков нет вообще.
##  - каждый бросок - независимая проверка с шансом ROLL_CHANCE_PERCENT (50%)
##    открыть одну случайную клетку территории соперника
##
## Архитектура как у CvAutoGrowthManager/CvAutoSpecialistManager - читай
## заголовок CvAutoGrowthManager.py за общими принципами. Отличие: тут не
## нужен CyMessageControl/sendModNetMessage, потому что единственное действие
## (plot.setRevealed) - это прямая правка синхронизированного состояния игры,
## а не клиентский UI-таск с проверкой владения активным игроком.
##
## Нюансы сетевой игры:
##  - Броски идут через gc.getGame().getSorenRandNum() - детерминированный РНГ
##    движка, одинаковый на всех клиентах. Модуль random из Python тут
##    недопустим - на разных клиентах вышли бы разные результаты и игра
##    расхинхронизировалась бы (OOS).
##  - onEndPlayerTurn вызывается движком одинаково и в одном порядке на всех
##    клиентах для каждого iPlayer - сама по себе логика по iPlayer
##    детерминирована. Но EspionagePoints - статистика КОМАНДЫ, а не игрока,
##    и при игре союзными командами (несколько игроков в одной команде)
##    onEndPlayerTurn вызовется несколько раз за один игровой ход команды -
##    посчитать её нужно ровно один раз за ход, иначе команда с большим
##    числом игроков получала бы больше бросков. Поэтому ниже есть
##    _lastProcessedTurn - отметка "эту команду в этот игровой ход уже
##    обработали".
##  - Никогда не завязывай эту логику на gc.getGame().getActivePlayer() или
##    getActiveTeam() - это локальный клиент, у разных игроков в сетевой игре
##    разное значение, и ветвление по нему привело бы к OOS.
##
## Производительность (важно при большом числе игроков/команд - иначе на
## каждую пару команд с преимуществом был бы отдельный проход по всей карте):
##  - Клетки по владельцам собираются ОДИН раз за игровой ход (на все команды
##    сразу, лениво - только если хоть кому-то в этот ход реально нужен
##    бросок), а не отдельно на каждую пару команд. Результат - словарь
##    eTeam -> список клеток этой команды, из него для выбора клетки просто
##    getSorenRandNum(len(list)) - O(1) без повторного сканирования карты.
##  - Мы не проверяем, была ли клетка уже открыта этой команде раньше - это
##    не критично (повторное setRevealed просто обновит информацию о клетке),
##    а исключение таких клеток потребовало бы фильтровать список под каждую
##    конкретную revealing-команду отдельно, а не один общий кеш по владельцу.

from CvPythonExtensions import *

gc = CyGlobalContext()

ADVANTAGE_PERCENT_PER_ROLL = 10	# шаг в % перевеса на одну попытку
ADVANTAGE_ROLLS_OFFSET = 2		# вычитается из (перевес // шаг); с шагом 10 даёт порог первой попытки в 30%
ROLL_CHANCE_PERCENT = 50		# шанс одного броска открыть одну клетку

_lastProcessedTurn = {}	# eTeam -> iGameTurn, чтобы не обработать одну команду дважды за ход

_iPlotCacheTurn = None		# игровой ход, на который построен _plotsByOwnerTeam (None - кеш ещё не строился)
_plotsByOwnerTeam = {}		# eTeam -> список клеток, которыми владеет эта команда (кеш на один игровой ход)


def _getAdvantagePercent(iMyEP, iTheirEP):
	'Перевес в % накопленных очков шпионажа одной команды над другой.'
	iBase = max(iTheirEP, 1)	# защита от деления на 0, когда у соперника EP ещё нет
	return ((iMyEP - iTheirEP) * 100) / iBase


def _countSuccessfulRolls(iAdvantagePercent, eRevealingTeam, eTargetTeam):
	iRolls = (iAdvantagePercent / ADVANTAGE_PERCENT_PER_ROLL) - ADVANTAGE_ROLLS_OFFSET
	if (iRolls <= 0):
		return 0

	iSuccesses = 0
	for i in range(iRolls):
		szLabel = "BetterEspionage: reveal roll %d, team %d vs %d" %(i, eRevealingTeam, eTargetTeam)
		if (gc.getGame().getSorenRandNum(100, szLabel) < ROLL_CHANCE_PERCENT):
			iSuccesses += 1

	return iSuccesses


def _ensurePlotCache():
	'Строит _plotsByOwnerTeam проходом по всей карте, не чаще одного раза за игровой ход - независимо от того, сколько команд/пар в этот ход запросят клетки.'
	global _iPlotCacheTurn, _plotsByOwnerTeam

	iCurrentTurn = gc.getGame().getGameTurn()
	if (_iPlotCacheTurn == iCurrentTurn):
		return

	_plotsByOwnerTeam = {}
	mapObj = gc.getMap()
	totalPlots = mapObj.numPlots()

	for i in range(totalPlots):
		plot = mapObj.plotByIndex(i)
		iOwner = plot.getOwner()
		if (iOwner == -1):
			continue
		eOwnerTeam = gc.getPlayer(iOwner).getTeam()
		_plotsByOwnerTeam.setdefault(eOwnerTeam, []).append(plot)

	_iPlotCacheTurn = iCurrentTurn


def _revealRandomPlots(eRevealingTeam, eTargetTeam, iCount):
	_ensurePlotCache()
	listCandidates = _plotsByOwnerTeam.get(eTargetTeam)
	if not listCandidates:
		return

	# Клетку, которая уже была раскрыта eRevealingTeam, можно выбрать снова -
	# это не ошибка, просто обновит её данные, а не каждый раз пересобирать
	# под каждую revealing-команду свой отдельный список непросмотренных клеток.
	for i in range(iCount):
		szLabel = "BetterEspionage: pick plot %d, team %d vs %d" %(i, eRevealingTeam, eTargetTeam)
		iPick = gc.getGame().getSorenRandNum(len(listCandidates), szLabel)
		listCandidates[iPick].setRevealed(eRevealingTeam, true, true, -1)


def _enforceTeamPair(eMyTeam, eTargetTeam):
	myTeam = gc.getTeam(eMyTeam)
	targetTeam = gc.getTeam(eTargetTeam)

	iMyEP = myTeam.getEspionagePointsAgainstTeam(eTargetTeam)
	iTheirEP = targetTeam.getEspionagePointsAgainstTeam(eMyTeam)

	iAdvantagePercent = _getAdvantagePercent(iMyEP, iTheirEP)
	iSuccesses = _countSuccessfulRolls(iAdvantagePercent, eMyTeam, eTargetTeam)

	if (iSuccesses > 0):
		_revealRandomPlots(eMyTeam, eTargetTeam, iSuccesses)


def enforceTeam(eTeam):
	'Раз в игровой ход сравнить очки шпионажа этой команды против всех встреченных живых соперников и, при достаточном перевесе, открыть им немного карты.'

	iCurrentTurn = gc.getGame().getGameTurn()
	if (_lastProcessedTurn.get(eTeam) == iCurrentTurn):
		return
	_lastProcessedTurn[eTeam] = iCurrentTurn

	team = gc.getTeam(eTeam)
	if (not team.isAlive()):
		return

	for eOtherTeam in range(gc.getMAX_CIV_TEAMS()):
		if (eOtherTeam == eTeam):
			continue

		otherTeam = gc.getTeam(eOtherTeam)
		if (not otherTeam.isAlive()):
			continue
		if (not team.isHasMet(eOtherTeam)):
			continue

		_enforceTeamPair(eTeam, eOtherTeam)


def enforcePlayer(iPlayer):
	'Вызывать раз в ход игрока (onEndPlayerTurn) - never from a UI click.'
	pPlayer = gc.getPlayer(iPlayer)

	if (pPlayer.isBarbarian() or pPlayer.isMinorCiv()):
		return

	enforceTeam(pPlayer.getTeam())
