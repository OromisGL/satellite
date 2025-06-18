//For now you can check this :     
// // ==============================
// 1. Define AOI: Germany
// ==============================
var germany = ee.FeatureCollection("FAO/GAUL/2015/level0")
    .filter(ee.Filter.eq("ADM0_NAME", "Germany"));
Map.centerObject(germany, 6);

// ==============================
// 2. Load CORINE Land Cover 2018
// ==============================
var corine = ee.Image("COPERNICUS/CORINE/V20/100m/2018").select("landcover");

// Create mask for forests (311–313) and agriculture (200–299)
var forestMask = corine.eq(311).or(corine.eq(312)).or(corine.eq(313));
var agriMask = corine.gte(200).and(corine.lt(300));
var combinedMask = forestMask.or(agriMask);

// ==============================
// 3. NDVI visualization style "normalized difference vegetation index" 
// ==============================
var ndviVis = {
    min: 0.0,
    max: 1.0,
    palette: ['white', 'yellow', 'green']
};

// ==============================
// 4. Define NDVI Processing Function
// ==============================
function processMODIS_NDVI(year) {
    var start = ee.Date.fromYMD(year, 9, 1);
    var end = ee.Date.fromYMD(year, 9, 30);

    var modisNDVI = ee.ImageCollection("MODIS/061/MOD13Q1")
        .filterDate(start, end)
        .select('NDVI')
        .map(function(img) {
        return img.multiply(0.0001).copyProperties(img, ['system:time_start']);
    });

    var medianNDVI = modisNDVI.median().clip(germany);

    // Apply forest + agriculture land cover mask
    var maskedNDVI = medianNDVI.updateMask(combinedMask).rename('NDVI_' + year);

    Map.addLayer(maskedNDVI, ndviVis, 'MODIS NDVI Sep ' + year + ' (F+A)');

    Export.image.toDrive({
        image: maskedNDVI,
        description: 'MODIS_NDVI_Sep_' + year + '_Forest_Agri',
        folder: 'MODIS_NDVI_Sep',
        region: germany.geometry(),
        scale: 250,
        crs: 'EPSG:4326',
        maxPixels: 1e13
    });
}

// ==============================
// 5. Loop for 2018 to 2024
// ==============================
[2018, 2019, 2020, 2021, 2022, 2023, 2024].forEach(processMODIS_NDVI);

// ==============================
// 6. Compute NDVI Change: 2024 − 2018
// ==============================
var start2018 = ee.Date.fromYMD(2018, 9, 1);
var end2018 = ee.Date.fromYMD(2018, 9, 30);
var start2024 = ee.Date.fromYMD(2024, 9, 1);
var end2024 = ee.Date.fromYMD(2024, 9, 30);

function getMaskedNDVI(start, end) {
    return ee.ImageCollection("MODIS/061/MOD13Q1")
        .filterDate(start, end)
        .select('NDVI')
        .map(function(img) {
        return img.multiply(0.0001).copyProperties(img, ['system:time_start']);
        })
        .median()
        .clip(germany)
        .updateMask(combinedMask);
}

var ndvi2018 = getMaskedNDVI(start2018, end2018).rename('NDVI_2018');
var ndvi2024 = getMaskedNDVI(start2024, end2024).rename('NDVI_2024');

// Calculate difference
var ndviChange = ndvi2024.subtract(ndvi2018).rename('NDVI_Change');

// ==============================
// 7. Visualize and Export NDVI Change
// ==============================
var changeVis = {
    min: -0.3,
    max: 0.3,
    palette: ['red', 'white', 'green']
};

Map.addLayer(ndviChange, changeVis, 'NDVI Change (2024 − 2018)');

Export.image.toDrive({
    image: ndviChange,
    description: 'MODIS_NDVI_Change_2024_2018_Forest_Agri',
    folder: 'MODIS_NDVI_Sep',
    region: germany.geometry(),
    scale: 250,
    crs: 'EPSG:4326',
    maxPixels: 1e13
});