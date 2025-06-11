
import ee
import geemap
import ee.batch

# Scaling Factor and Offset from Google Engine Docs
SCALE = 0.00341802
OFFSET = 149.0

# Temperature Scale in Kelin 
T_MIN_K = 270
T_MAX_K = 330

# Dynamic transfer from Kelvin → DN
dn_min = (T_MIN_K - OFFSET) / SCALE
dn_max = (T_MAX_K - OFFSET) / SCALE

def get_country_geometry(name: str) -> ee.Geometry:
    """
    Liest die Ländergrenzen aus und gibt die Geometry des gesuchten Landes zurück.
    """
    countries = ee.FeatureCollection("WM/geoLab/geoBoundaries/600/ADM0")
    country_feature = countries \
        .filter(ee.Filter.eq("shapeName", name)) \
        .first()
    if country_feature is None:
        raise ValueError(f"Land '{name}' nicht gefunden in GeoBoundaries.")
    return country_feature.geometry()

def dn_to_kelvin(dn_image: ee.Image) -> ee.Image:
    """Konvertiert das DN-Band in Kelvin."""
    return dn_image.multiply(SCALE).add(OFFSET)

def kelvin_to_celsius(k_image: ee.Image) -> ee.Image:
    """Konvertiert Kelvin in Celsius."""
    return k_image.subtract(273.15)

# 4. Funktion zur Maskierung von ST_B10-Pixeln außerhalb 290–310 K
def mask_lst_range(image: ee.Image) -> ee.Image:
    """
    Erstellt eine Maske für alle Pixel, deren ST_B10-Wert
    (ungebräunt) zwischen 41233 und 47085 liegt,
    und skaliert anschließend auf Celsius.
    """
    
    # 270–330 K in digital_number-Werten (vor Skalierung): 270/0.00341802 - 149 ≈ 41233, 330/0.00341802 - 149 ≈ 47085
    digital_number = image.select("ST_B10")
    # checking the Quality with QA_PIXEL
    qa_pixel = image.select("QA_PIXEL")
    
    # less restrectiv Temperature Mask
    temp_mask = digital_number.gte(dn_min).And(digital_number.lte(dn_max))
    
    # just the worst Pixel get canceled
    qa_mask = qa_pixel.bitwiseAnd(1 << 3).eq(0)
    
    # combining the Masks
    combined_mask = temp_mask.And(qa_mask)
    
    # LST Cinverting
    k_image = dn_to_kelvin(digital_number)
    lst_c = kelvin_to_celsius(k_image)
    
    # Add mask
    lst_c_masked = lst_c.updateMask(combined_mask)
    
    # lst_c = digital_number.multiply(SCALE).add(OFFSET).subtract(273.15)
    return image.addBands(lst_c_masked.rename("LST_Celsius"))



# 5. MULTI-TEMPORAL COMPOSITING mit verschiedenen Strategien
def create_gap_filled_composite(collection):
    """
    Erstellt ein lückengefülltes Komposit mit mehreren Strategien
    """
    # Bilder verarbeiten
    processed = collection.map(mask_lst_range)
    lst_collection = processed.select("LST_Celsius")
    
    # Strategie 1: Median (bevorzugt)
    median_composite = lst_collection.median()
    
    # Strategie 2: Mean für verbleibende Lücken
    mean_composite = lst_collection.mean()
    
    # Strategie 3: Räumliche Interpolation für kleine Lücken
    # Verwende den Median wo verfügbar, sonst den Mean
    final_composite = median_composite.unmask(mean_composite)
    
    return final_composite

def process_modis(image):
    def has_qc_day_fn(img):
        qa = img.select("QC_Day")
        lst_k = img.select("LST_Day_1km").multiply(0.02)
        lst_c = lst_k.subtract(273.15)
        quality_mask = qa.bitwiseAnd(3).lte(1)
        return lst_c.updateMask(quality_mask).rename("LST_Celsius_MODIS")

    def fallback_fn(img):
        lst_k = img.select("LST_Day_1km").multiply(0.02)
        lst_c = lst_k.subtract(273.15)
        return lst_c.rename("LST_Celsius_MODIS")

    return ee.Image(
        ee.Algorithms.If(
            image.bandNames().contains("QC_Day"),
            has_qc_day_fn(image),
            fallback_fn(image)
        )
    )

# 6. ZUSÄTZLICHE DATENQUELLEN für Gap-Filling
def add_modis_data_for_gaps(landsat_composite, country_geom):
    """
    Fügt MODIS LST Daten hinzu um Lücken zu füllen
    """
    # MODIS Terra LST (niedrigere Auflösung aber bessere zeitliche Abdeckung)
    modis_collection = (
        ee.ImageCollection("MODIS/061/MOD11A1")
        .filterDate("2023-06-01", "2023-09-01")
        .filterBounds(country_geom)
        .select("LST_Day_1km")
    )
    
    modis_processed = modis_collection.map(process_modis)
    modis_median = modis_processed.median()
    
    # MODIS auf Landsat-Auflösung resamplen
    modis_resampled = modis_median.resample('bilinear').reproject(
        crs='EPSG:4326',
        scale=30
    )
    
    # Landsat wo verfügbar, sonst MODIS
    gap_filled = landsat_composite.unmask(modis_resampled)
    
    return gap_filled

def visual_map(final_result, country_geom):
    # Map visualisieren
    m = geemap.Map()
    vis_params = {
        "bands": ["LST_Celsius"],
        "min": 0,    # 0 °C
        "max": 40,   # 40 °C
        "palette": ["blue", "green", "yellow", "red"]
    }

    m.add_layer(final_result, vis_params, "Landsat-9 LST (°C)")
    m.center_object(country_geom, 6)

    # 7. Karte speichern und Verbindung bestätigen
    return m.to_html("landsat_lst_map.html")

def export_to_drive(final_result, country_geom):
    export_task = ee.batch.Export.image.toAsset(
    image=final_result,
    description='LST_Germany_2023_gap_filled_drive',
    assetId='projects/impressive-bay-447915-g8/assets/Germany_LST_gap_filled',
    region=country_geom,
    scale=30,
    maxPixels=1e13,
    crs='EPSG:4326'
    )

    export_task.start()
    
def collections(dataset, country_geom, start, end, cloud='CLOUD_COVER'):
    """_summary_

    Args:
        dataset (String): _description_
        country_geom: geo information 
        start (Stirng): Start Date
        end (String): End Date
        cloud (str, optional): Filter for Coud Cover. Defaults to 'CLOUD_COVER'.

    Returns:
        ImageCollection
    """
    return (
    ee.ImageCollection(dataset)
    .filterDate(start, end)
    .filterBounds(country_geom)
    .filter(ee.Filter.lt(cloud, 50))
)