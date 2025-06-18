import ee
from utils import filter_bounds_geojson, get_img_from_projects, img_collection, images_to_pdf

ee.Initialize(project='impressive-bay-447915-g8')

#img = get_img_from_projects('NDVI_COPERNICUS/COPERNICUS_NDVI_Sep_2018_2024_VEGITAION_Ukraine')

img_collection_germany = img_collection('projects/impressive-bay-447915-g8/assets/weekly_lsts_forest_agri/')

bounds_geojson = filter_bounds_geojson('Germany')


xs = [p[0] for p in bounds_geojson['coordinates'][0]]
ys = [p[1] for p in bounds_geojson['coordinates'][0]]
dx = max(xs) - min(xs)
dy = max(ys) - min(ys)
W = 800
H = round(W * (dy / dx))

# stats = img.reduceRegion(
#     reducer=ee.Reducer.minMax(),
#     geometry=bounds_geojson,
#     scale=200,
#     bestEffort=True,
#     maxPixels=1e9
# ).getInfo()

min_temp = 0
max_temp = 1.0

# 4. Palette definieren (Hex-Codes von kalt → warm)
palette = [
    'white',
    'yellow',
    'green'
]

vis_params = {
    'min': min_temp,         
    'max': max_temp,          
    'palette': palette
}

thumb_params = {
    'region': bounds_geojson,
    'scale': 290,
    'crs': 'EPSG:3035',
    'width': W,
    'height': H,
    'format': 'png',
    'transparent': True,
    **vis_params
}


for img in img_collection_germany[2:]:
    url = img.getThumbURL(thumb_params)
    asset_id = img.get('system:id').getInfo().split('/')[-1]
    import requests
    r = requests.get(url)
    with open(f'Images/German_NDVI_{asset_id}.png', 'wb') as f:
        f.write(r.content)