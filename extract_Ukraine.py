import ee
from utils import filter_bounds_geojson, get_img_from_projects

ee.Initialize(project='impressive-bay-447915-g8')

img = get_img_from_projects('NDVI_COPERNICUS/COPERNICUS_NDVI_Sep_2018_2024_VEGITAION_Ukraine')



bounds_geojson = filter_bounds_geojson('Ukraine')


xs = [p[0] for p in bounds_geojson['coordinates'][0]]
ys = [p[1] for p in bounds_geojson['coordinates'][0]]
dx = max(xs) - min(xs)
dy = max(ys) - min(ys)
W = 800
H = round(W * (dy / dx))

stats = img.reduceRegion(
    reducer=ee.Reducer.minMax(),
    geometry=bounds_geojson,
    scale=200,
    bestEffort=True,
    maxPixels=1e9
).getInfo()

min_change = -0.3
max_change = 0.3

# 4. Palette definieren (Hex-Codes von kalt → warm)
palette = [
    'red', 
    'white', 
    'green'
]

vis_params = {
    'min': min_change,         
    'max': max_change,          
    'palette': palette
}

thumb_params = {
    'region': bounds_geojson,
    'dimensions': '3200',
    'crs': 'EPSG:3035',
    'width': W,
    'height': H,
    'format': 'png',
    **vis_params
}

url = img.getThumbURL(thumb_params)

import requests
r = requests.get(url)
with open('Images/Ukraine_NDVI_Sep_2018_2024_VEGITAION.png', 'wb') as f:
    f.write(r.content)
