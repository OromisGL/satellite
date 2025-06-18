import ee
from utils import *

ee.Initialize(project='impressive-bay-447915-g8')

country_geom = get_country_geometry("Ukraine")

# Lade eine einzelne Sentinel-2 SR-Szene (Level-2A)
s2 = ee.ImageCollection('COPERNICUS/S2_SR') \
    .filterDate('2024-09-01', '2024-09-30') \
    .filterBounds(country_geom)  # Ihre Ukraine-Geometrie
scene = ee.Image(s2.first())

# ndvi = full.normalizedDifference(['B8','B4']).rename('NDVI')

# Geben Sie die Bandliste aus
print(scene.bandNames().getInfo())

