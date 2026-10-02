## Utopia mod - shared helper for Cyrillic Steam nickname repair
import CvUtil

CYRILLIC_RANGE_LOW = u"\u0400"
CYRILLIC_RANGE_HIGH = u"\u04FF"

def fixNetworkPlayerName(raw, tag="?"):
	"""Repairs Cyrillic Steam nicknames that reach the engine as UTF-8 bytes.

	The game's bitmap font is indexed by raw byte value (0-255), the same way
	TXT_KEY_* entries store Cyrillic as &#NNN; where NNN is the cp1251 byte of
	each letter - not a real Unicode code point. So a player name has to be
	converted the same way: decode the genuine UTF-8 bytes Steam provided,
	re-encode as cp1251, then present those bytes as code points 0-255 (via
	latin-1) so the font looks them up correctly. We only accept the result if
	it decodes cleanly AND actually contains Cyrillic letters - otherwise the
	original value is returned untouched so non-Russian names are never hit.

	Only works where Python actually builds the on-screen string (scoreboard,
	advisor screens, dropdowns, tables, etc). The pre-game multiplayer lobby
	and the live chat window are drawn natively by the exe and never pass
	through this function.

	'tag' identifies the call site in PythonDbg.log (every call is logged,
	success or not) so it's possible to tell which screens actually reach
	this function and what raw data they hand it.
	"""
	try:
		CvUtil.pyPrint("fixNetworkPlayerName[%s]: input=%s" %(tag, repr(raw)))
	except Exception:
		pass

	if raw is None:
		return raw
	try:
		if isinstance(raw, unicode):
			rawBytes = raw.encode('latin-1')
		else:
			rawBytes = raw
	except (UnicodeEncodeError, TypeError):
		try:
			CvUtil.pyPrint("fixNetworkPlayerName[%s]: skip, could not get raw bytes" %(tag,))
		except Exception:
			pass
		return raw

	try:
		realText = rawBytes.decode('utf-8')
	except UnicodeDecodeError:
		try:
			CvUtil.pyPrint("fixNetworkPlayerName[%s]: skip, not valid UTF-8" %(tag,))
		except Exception:
			pass
		return raw

	bHasCyrillic = False
	for ch in realText:
		if ch >= CYRILLIC_RANGE_LOW and ch <= CYRILLIC_RANGE_HIGH:
			bHasCyrillic = True
			break
	if not bHasCyrillic:
		try:
			CvUtil.pyPrint("fixNetworkPlayerName[%s]: skip, no Cyrillic found after UTF-8 decode (%s)" %(tag, repr(realText)))
		except Exception:
			pass
		return raw

	try:
		fixedName = realText.encode('cp1251').decode('latin-1')
	except UnicodeEncodeError:
		try:
			CvUtil.pyPrint("fixNetworkPlayerName[%s]: skip, cp1251 encode failed" %(tag,))
		except Exception:
			pass
		return raw

	try:
		CvUtil.pyPrint("fixNetworkPlayerName[%s]: repaired %s -> %s" %(tag, repr(raw), repr(fixedName)))
	except Exception:
		pass

	return fixedName
