import ee

ee.Initialize(project='impressive-bay-447915-g8')

img = ee.Image('projects/impressive-bay-447915-g8/assets/Germany_LST_gap_filled')

region = ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017")

bounds_geojson = region.filter(ee.Filter.eq('country_na', 'Germany')).geometry().bounds().getInfo()


xs = [p[0] for p in bounds_geojson['coordinates'][0]]
ys = [p[1] for p in bounds_geojson['coordinates'][0]]
dx = max(xs) - min(xs)
dy = max(ys) - min(ys)
W = 800
H = round(W * (dy / dx))

stats = img.reduceRegion(
    reducer=ee.Reducer.minMax(),
    geometry=bounds_geojson,
    scale=30,
    maxPixels=1e9
).getInfo()

min_temp = 0
max_temp = 40

# 4. Palette definieren (Hex-Codes von kalt → warm)
palette = [
    '#040274',  # sehr kalt
    '#0909F9',
    '#27E2E2',
    '#7FE641',
    '#FFE100',
    '#FF6A00',
    '#9B0000'   # sehr heiß
]

vis_params = {
    'min': min_temp,         
    'max': max_temp,          
    'palette': palette
}

thumb_params = {
    'region': bounds_geojson,
    'crs': 'EPSG:3035',
    'scale': 290,
    'width': W,
    'height': H,
    'format': 'png',
    **vis_params
}

url = img.getThumbURL(thumb_params)

import requests
r = requests.get(url)
with open('lst_de_thumbnail.png', 'wb') as f:
    f.write(r.content)
