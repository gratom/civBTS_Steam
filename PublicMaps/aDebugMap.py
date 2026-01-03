from CvPythonExtensions import *
import CvUtil
import CvMapGeneratorUtil
from CvMapGeneratorUtil import FractalWorld
from CvMapGeneratorUtil import TerrainGenerator
from CvMapGeneratorUtil import FeatureGenerator
import sys

def getDescription():
	"Description shown in the main menu"
	return "Smallest possible map used for debugging"

def isAdvancedMap():
	"This map should show up in simple mode, but only in debug builds"
	return not CyGlobalContext().isDebugBuild()

def getGridSize(argsList):
	"Because this is such a land-heavy map, override getGridSize() to make the map smaller"
	grid_sizes = {
		WorldSizeTypes.WORLDSIZE_DUEL:   (5,5),
		WorldSizeTypes.WORLDSIZE_TINY:   (5,5),
		WorldSizeTypes.WORLDSIZE_SMALL:  (5,5),
		WorldSizeTypes.WORLDSIZE_STANDARD: (5,5),
		WorldSizeTypes.WORLDSIZE_LARGE:  (5,5),
		WorldSizeTypes.WORLDSIZE_HUGE:   (5,5)
	}

	if (argsList[0] == -1): # (-1,) is passed to function on loads
		return []
	[eWorldSize] = argsList
	return grid_sizes[eWorldSize]

def getWrapX(): return False
def getWrapY(): return False

def generatePlotTypes():
	NiTextOut("Setting Plot Types (Python Continents) ...")
	fractal_world = FractalWorld()
	fractal_world.initFractal()
	return fractal_world.generatePlotTypes()

def generateTerrainTypes():
	NiTextOut("Generating Terrain (Python Continents) ...")
	terraingen = TerrainGenerator()
	terrainTypes = terraingen.generateTerrain()
	return terrainTypes

def addFeatures():
	NiTextOut("Adding Features (Python Continents) ...")
	featuregen = FeatureGenerator()
	featuregen.addFeatures()
	return 0
