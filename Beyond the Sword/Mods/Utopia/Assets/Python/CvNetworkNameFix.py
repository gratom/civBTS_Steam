## Utopia mod - shared helper for Cyrillic Steam nickname repair
import re

CYRILLIC_RANGE_LOW = u"\u0400"
CYRILLIC_RANGE_HIGH = u"\u04FF"

# Matches a run of plain ASCII mixed with 2-byte UTF-8 Cyrillic sequences
# (lead byte \xd0-\xd3, continuation \x80-\xbf covers U+0400-U+04FF). Native
# engine strings that are ALREADY correct Cyrillic use a different single
# byte-per-letter scheme (see fixNetworkPlayerName's docstring), so they never
# match this pattern - only a raw UTF-8 name embedded in the string does.
_UTF8_CYRILLIC_RUN = re.compile(r'(?:[\x20-\x7e]|[\xd0-\xd3][\x80-\xbf])*[\xd0-\xd3][\x80-\xbf](?:[\x20-\x7e]|[\xd0-\xd3][\x80-\xbf])*')

def fixNetworkPlayerName(raw):
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
	"""
	if raw is None:
		return raw
	try:
		if isinstance(raw, unicode):
			rawBytes = raw.encode('latin-1')
		else:
			rawBytes = raw
	except (UnicodeEncodeError, TypeError):
		return raw

	try:
		realText = rawBytes.decode('utf-8')
	except UnicodeDecodeError:
		return raw

	bHasCyrillic = False
	for ch in realText:
		if ch >= CYRILLIC_RANGE_LOW and ch <= CYRILLIC_RANGE_HIGH:
			bHasCyrillic = True
			break
	if not bHasCyrillic:
		return raw

	try:
		fixedName = realText.encode('cp1251').decode('latin-1')
	except UnicodeEncodeError:
		return raw

	return fixedName

def fixEmbeddedPlayerNames(text):
	"""Repairs a raw UTF-8 Cyrillic player name embedded INSIDE a larger,
	already-built native string - e.g. CyInterface().getHelpString(), which
	the engine assembles itself and Python only displays. Unlike
	fixNetworkPlayerName, this does not require the WHOLE string to be valid
	UTF-8 (it won't be - the surrounding native Cyrillic text, if any, uses
	the single byte-per-letter scheme, not real UTF-8). Instead it scans for
	the one embedded run that looks like UTF-8 Cyrillic, repairs only that
	span, and leaves everything else byte-for-byte untouched.
	"""
	if text is None:
		return text
	try:
		if isinstance(text, unicode):
			rawBytes = text.encode('latin-1')
		else:
			rawBytes = text
	except (UnicodeEncodeError, TypeError):
		return text

	match = _UTF8_CYRILLIC_RUN.search(rawBytes)
	if not match:
		return text

	szSpan = match.group(0)
	try:
		uSpan = szSpan.decode('utf-8')
	except UnicodeDecodeError:
		return text

	nCyrillic = 0
	for ch in uSpan:
		if ch >= CYRILLIC_RANGE_LOW and ch <= CYRILLIC_RANGE_HIGH:
			nCyrillic += 1
	if nCyrillic < 2:
		return text

	try:
		fixedSpanBytes = uSpan.encode('cp1251')
	except UnicodeEncodeError:
		return text

	newBytes = rawBytes[:match.start()] + fixedSpanBytes + rawBytes[match.end():]

	try:
		return newBytes.decode('latin-1')
	except UnicodeDecodeError:
		return text
