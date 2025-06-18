import ee
from utils import *

#Copernicus Variables
LEAVED_FOREST = 311 #Forest and semi natural areas > Forests > Broad-leaved forest 
CONIFEROUS_FOREST = 312 # Forest and semi natural areas > Forests > Coniferous forest 
MIXED_FOREST = 313 #Forest and semi natural areas > Forests > Mixed forest 

# Modis Variables


# # GEE init
ee.Initialize(project='impressive-bay-447915-g8')

# 1. Laden des Klassifizierungsbands für die Masken 
col = ee.ImageCollection("COPERNICUS/Landcover/100m/Proba-V-C3/Global")
# a) Erstes Bild in der Collection
snap = col.first()  

cgls = snap.select("discrete_classification")
# 2. Wald-Masken:  
#    • 40 = Tree cover, broadleaved  
#    • 50 = Tree cover, coniferous  
forestMask = cgls.eq(40).Or(cgls.eq(50))

# 3. Agrar-Maske: 30 = Cropland
agriMask   = cgls.eq(30)

# 4. Kombiniert
combinedMask = forestMask.Or(agriMask)

# get Bands 4 and 8 vor NDVI Spectrum. Need to Compute the Normalized Difference between them afterwards


# # Geo Information of Target Country
Ukraine = get_country_geometry("Ukraine")



list_year = [2018, 2019, 2020, 2021, 2022, 2023, 2024]

ndvi_2018 = get_masked_NDVI("COPERNICUS/S2_HARMONIZED", Ukraine, combinedMask, list_year[0], ["B8", "B4"])
ndvi_2024 = get_masked_NDVI("COPERNICUS/S2_HARMONIZED", Ukraine, combinedMask, list_year[-1], ["B8", "B4"])
# Calculate Difference between start and end
ndviChange = ndvi_2024.subtract(ndvi_2018).rename('NDVI_Change')

export_masked_NDVI("NDVI_COPERNICUS", "UKRAINE_NDVI_CHANGE_2018_2024", ndviChange, 'projects/impressive-bay-447915-g8/assets/NDVI_COPERNICUS', Ukraine, list_year[0], list_year[-1])
