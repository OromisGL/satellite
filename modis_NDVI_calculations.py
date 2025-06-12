import ee
from utils import *

#Copernicus Variables
LEAVED_FOREST = 311 #Forest and semi natural areas > Forests > Broad-leaved forest 
CONIFEROUS_FOREST = 312 # Forest and semi natural areas > Forests > Coniferous forest 
MIXED_FOREST = 313 #Forest and semi natural areas > Forests > Mixed forest 

# # GEE init
ee.Initialize(project='impressive-bay-447915-g8')

# # select Land Cover from 2018
corine = getIMG("COPERNICUS/CORINE/V20/100m/2018", "landcover")

# # Geo Information of Target Country
country_geom = get_country_geometry("Germany")
# creating masks for Forests
forestMask = select_mask_OR(corine, LEAVED_FOREST, CONIFEROUS_FOREST, MIXED_FOREST)

# creating masks for Agriculure
agriMask = corine.gte(200).And(corine.lt(300))

#merging the two sets of Masks
combinedMask = forestMask.Or(agriMask)

# loop for 2018 to 2024 for NDVI 

list_year = [2018, 2019, 2020, 2021, 2022, 2023, 2024]

ndvi2018 = get_masked_MODIS_NDVI(list_year[0], country_geom, combinedMask).rename('NDVI_2018')
ndvi2024 = get_masked_MODIS_NDVI(list_year[-1], country_geom, combinedMask).rename('NDVI_2024')

# Calculate Difference between start and end
ndviChange = ndvi2024.subtract(ndvi2018).rename('NDVI_Change')

export_masked_MODIS_NDVI(ndviChange, 'projects/impressive-bay-447915-g8/assets/weekly_lsts_forest_agri', country_geom, 2018, 2024)

# for year in list_year:
#     processMODIS_NDVI(year, country_geom, combinedMask, 'projects/impressive-bay-447915-g8/assets/weekly_lsts_forest_agri')
#     print(f"Uploading Image {year} ...")
