import ee

# importing all the custom Functions from utils.py
from utils import *

# # GEE init
ee.Initialize(project='impressive-bay-447915-g8')

# # Geo Information of Target Country
country_geom = get_country_geometry("Germany")

# # Landsat-9 collection for summer 2023
# collection = collections("LANDSAT/LC09/C02/T1_L2", country_geom, "2023-05-01", "2023-10-01")

# print("Anzahl Bilder nach räumlicher Filterung:", collection.size().getInfo())

# print('Creating Landsat Composite...')
# landsat_compsite = create_gap_filled_composite(collection)

# print("Filling the Gaps with Modis Data...")
# gap_filled_composite = add_modis_data_for_gaps(landsat_compsite, country_geom)

# Clipping the final Dataset
# final_result = gap_filled_composite.clip(country_geom)

# Uncomment a Function below to use it:

# visual_map(final_result, country_geom)

# export_to_drive(final_result, country_geom)

# def calculate_coverage_stats(image, geometry):
#     """Berechnet Statistiken über die Datenabdeckung"""
#     # Pixel mit gültigen Daten zählen
#     valid_pixels = image.select(0).mask().reduceRegion(
#         reducer=ee.Reducer.sum(),
#         geometry=geometry,
#         scale=1000,  # Gröbere Auflösung für Statistik
#         maxPixels=1e10
#     )

#     # Gesamte Pixel zählen
#     total_pixels = ee.Image(1).reduceRegion(
#         reducer=ee.Reducer.sum(),
#         geometry=geometry,
#         scale=1000,
#         maxPixels=1e10
#     )

#     return valid_pixels, total_pixels

# # Statistiken berechnen (optional)
# valid_stats, total_stats = calculate_coverage_stats(final_result, country_geom)
# print("Datenabdeckungs-Statistiken:")

# print("Gesamt Pixel:", total_stats.getInfo())

# print(ee.String("GEE-Verbindung OK").getInfo())


