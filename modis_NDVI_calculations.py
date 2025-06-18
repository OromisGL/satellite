import ee
from utils import *

#Copernicus Variables
LEAVED_FOREST = 311 #Forest and semi natural areas > Forests > Broad-leaved forest 
CONIFEROUS_FOREST = 312 # Forest and semi natural areas > Forests > Coniferous forest 
MIXED_FOREST = 313 #Forest and semi natural areas > Forests > Mixed forest 

# Modis Variables


# # GEE init
ee.Initialize(project='impressive-bay-447915-g8')

# # select Land Cover from 2018 for EU
corine_EU = getIMG("COPERNICUS/CORINE/V20/100m/2018", "landcover")

# select Land Cover Data for World Wide
# corine_World = getIMG("ESA/WorldCover/v1008", "landcover")



# # Geo Information of Target Country
# Ukraine = get_country_geometry("Ukraine")
Germany = get_country_geometry("Germany")


# creating masks for Forests EU
# forestMask = select_mask_OR(corine_EU, LEAVED_FOREST, CONIFEROUS_FOREST, MIXED_FOREST)

# creating mask World Wide
forestMask = select_mask_OR(corine_EU, LEAVED_FOREST, CONIFEROUS_FOREST, MIXED_FOREST)

# creating masks for Agriculure EU
# agriMask = corine_EU.gte(200).And(corine_EU.lt(300)) 

# creating Mask from world WIde Data
agriMask = corine_EU.gte(200).And(corine_EU.lt(300))

#merging the two sets of Masks
combinedMask = forestMask.Or(agriMask)

# loop for 2018 to 2024 for NDVI 

list_year = [2018, 2019, 2020, 2021, 2022, 2023, 2024]

# 

ndvi2018 = get_masked_MODIS_NDVI(list_year[0], Germany, combinedMask, "MODIS/061/MOD13Q1").rename('NDVI_2018')
ndvi2024 = get_masked_MODIS_NDVI(list_year[-1], Germany, combinedMask, "MODIS/061/MOD13Q1").rename('NDVI_2024')

# Calculate Difference between start and end
ndviChange = ndvi2024.subtract(ndvi2018).rename('NDVI_Change')

export_masked_MODIS_NDVI(ndviChange, 'projects/impressive-bay-447915-g8/assets/weekly_lsts_forest_agri', Germany, list_year[0], list_year[-1])

# for year in list_year:
#     processMODIS_NDVI(year, country_geom, combinedMask, 'projects/impressive-bay-447915-g8/assets/weekly_lsts_forest_agri')
#     print(f"Uploading Image {year} ...")
