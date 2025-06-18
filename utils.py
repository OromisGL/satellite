
import ee
import geemap
import ee.batch
import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, portrait
from reportlab.lib.units import cm
import glob
import os

# Scaling Factor and Offset from Google Engine Docs
SCALE = 0.00341802
OFFSET = 149.0

# Temperature Scale in Kelin 
T_MIN_K = 270
T_MAX_K = 330

# Dynamic transfer from Kelvin → DN
dn_min = (T_MIN_K - OFFSET) / SCALE
dn_max = (T_MAX_K - OFFSET) / SCALE

# Create different Masks for Forest

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
    
    
def weekly(weeks, collection):
    for start, end in weeks:
        week_img = collection.filterDate(start, end).mean()
        
def select_mask_OR(region, *classes):
    """_summary_

    Args:
        region (GEO INfo
        classes: a list of numbers, each refers to a class from the Satillite Data
    """
    mask = region.eq(classes[0])
    
    for cls in classes[1:]:
        mask = mask.Or(region.eq(cls))
    return mask

def select_mask_AND(region, *classes):
    """_summary_

    Args:
        region (GEO INfo
        classes: a list of numbers, each refers to a class from the Satillite Data
    """
    mask = region.eq(classes[0])
    
    for cls in classes[1:]:
        mask = mask.And(region.eq(cls))
    return mask

def combine_mask_OR(*mask):
    
    mask = mask[0]
    
    for layer in mask[1:]:
        mask = mask.And(layer)
    return mask
        
def processMODIS_NDVI(year, region, masks, out_folder):
    start = ee.Date.fromYMD(year, 9, 1)
    end = ee.Date.fromYMD(year, 9, 30)
    
    modisNDVI = ee.ImageCollection("MODIS/061/MOD13Q1") \
        .filterDate(start, end) \
        .select('NDVI') \
        .map(lambda img: img 
            .multiply(0.0001)
            .copyProperties(img, ['system:time_start']))
        
    medianNDVI = modisNDVI.median().clip(region)
    
    maskedNDVI = medianNDVI.updateMask(masks).rename('NDVI_' + str(year))
    
    task = ee.batch.Export.image.toAsset(
        image=maskedNDVI,
        description=f"MODIS_NDVI_Sep_{str(year)}",
        assetId=f"{out_folder}/MODIS_NDVI_Sep_{str(year)}_Forest_Agri",
        region=region,
        scale=250,
        crs='EPSG:4326',
        maxPixels=1e13
        )
    task.start()
    
def getIMG(name, type):
    """_summary_

    Args:
        name (String): name of the Data collection
        type (String): type of the Data we need for processing 

    Returns:
        ee.Image:
    """
    return ee.Image(name).select(type)

def get_masked_MODIS_NDVI(year, region, masks, image_collection):
    start = ee.Date.fromYMD(year, 9, 1)
    end = ee.Date.fromYMD(year, 9, 30)
    
    return ee.ImageCollection(image_collection) \
        .filterDate(start, end) \
        .select('NDVI') \
        .map(lambda img: img 
            .multiply(0.0001)
            .copyProperties(img, ['system:time_start'])).median().clip(region).updateMask(masks)

def export_masked_MODIS_NDVI(ndviChange,out_folder, region, start, end):
    task = ee.batch.Export.image.toAsset(
        image=ndviChange,
        description=f"MODIS_NDVI_Change_Sep_{str(start)}_{str(end)}",
        assetId=f"{out_folder}/MODIS_NDVI_Sep_{str(start)}_{str(end)}_Forest_Agri_Ukraine",
        region=region,
        scale=250,
        crs='EPSG:4326',
        maxPixels=1e13
        )
    task.start()
    
    
def export_masked_COPERNICUS_NDVI(ndviChange, out_folder, region, start, end):
    task = ee.batch.Export.image.toAsset(
        image=ndviChange,
        description=f"COPERNICUS_NDVI_Change_Sep_{str(start)}_{str(end)}",
        assetId=f"{out_folder}/COPERNICUS_NDVI_Sep_{str(start)}_{str(end)}_VEGITAION_Ukraine",
        region=region,
        scale=200,
        crs='EPSG:4326',
        maxPixels=1e13
        )
    task.start()
    
def get_masked_COPERNICUS(year, region, masks, image_collection):
    start = ee.Date.fromYMD(year, 9, 1)
    end = ee.Date.fromYMD(year, 9, 30)
    
    return ee.ImageCollection(image_collection) \
        .filterDate(start, end) \
        .clip(region) \
        .updateMask(masks)
        

def get_masked_NDVI(collection_id, region, mask, year, bands=None):
    """_summary_

    Args:
        collection_id (String): input of the collection ID e.g. "COPERNICUS/S2_HARMONIZED"
        region (geomentry Data): use get_country_geometry
        mask (img Mask): combine masks befor
        year (int): year you wanna exploit
        bands (String or list of Strings, optional): select the bands you wanna use. Defaults to None.

    Returns:
        _type_: _description_
    """
    start = ee.Date.fromYMD(year, 1, 1)
    end = ee.Date.fromYMD(year, 12, 30)
    col = ee.ImageCollection(collection_id) \
            .filterDate(start, end) \
            .filterBounds(region)

    if bands:  # Sentinel-2
        # 1) nur B4/B8 auswählen, 2) skalieren, 3) NDVI berechnen
        img = col.median().select(bands).multiply(0.0001)
        ndvi = img.normalizedDifference(bands).rename('NDVI')
    else:      # MODIS
        # 1) MODIS liefert schon ein NDVI-Band, 2) skalieren
        ndvi = col.select('NDVI') \
                .map(lambda i: i.multiply(0.0001)
                .copyProperties(i,['system:time_start'])) \
                .median()

    # 3) clip & mask anwenden
    return ndvi.clip(region).updateMask(mask)

def export_masked_NDVI(suffix, prefix, ndviChange, out_folder, region, start, end):
    task = ee.batch.Export.image.toAsset(
        image=ndviChange,
        description=f"{suffix}_{str(start)}_{str(end)}",
        assetId=f"{out_folder}/{suffix}{str(start)}_{str(end)}_{prefix}",
        region=region,
        scale=200,
        crs='EPSG:4326',
        maxPixels=1e13
        )
    task.start()
    
def filter_bounds_geojson(country):
    """_summary_

    Args:
        country (String): Country Name
        
    """
    region = ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017")
    
    return region.filter(ee.Filter.eq('country_na', country)).geometry().bounds().getInfo()
    
    
def get_img_from_projects(imgPath):
    """
    Args:
        imgPath: (String) Name of the GEE Folder to fetch the Img Data and Name of the img File
    """
    return ee.Image(f'projects/impressive-bay-447915-g8/assets/{imgPath}')

def img_collection(folder_path):
    
    assets = ee.data.listAssets({'parent': folder_path})['assets']
    ids = [a['id'] for a in assets]
    
    return [ee.Image(id) for id in ids]

def images_to_pdf(image_folder: str, output_pdf: str, descriptions: dict):
    """
    Erzeugt ein mehrseitiges PDF (DIN A4 Hochformat) mit:
        - je einer PNG pro Seite (proportional skaliert, weißer Hintergrund)
        - individueller Beschreibung oberhalb des Bildes
        - Legende unterhalb des Bildes
    `descriptions` ist ein Dict: {basename_ohne_ext: Beschreibungstext}.
    """
    # Canvas anlegen
    c = canvas.Canvas(output_pdf, pagesize=portrait(A4))
    page_w, page_h = portrait(A4)
    
    # Ränder und nutzbare Fläche
    margin = 1 * cm
    usable_w = page_w - 2 * margin
    usable_h = page_h - 2 * margin
    
    # Alle Bilder einlesen
    image_paths = sorted(glob.glob(os.path.join(image_folder, "German_NDVI_*.png")))
    if not image_paths:
        raise FileNotFoundError(f"Keine PNGs in {image_folder} gefunden.")
    
    for img_path in image_paths:
        # (1) Weißer Hintergrund
        c.setFillColorRGB(1, 1, 1)
        c.rect(0, 0, page_w, page_h, fill=1, stroke=0)
        
        # (2) Beschreibung ermitteln
        basename = os.path.splitext(os.path.basename(img_path))[0]
        desc = descriptions.get(basename)
        
        if desc:
            c.setFillColorRGB(0, 0, 0)
            c.setFont("Helvetica", 11)
            # Text oberhalb des Bild-Rahmens
            text_x = margin
            text_y = margin + usable_h + 0.5 * cm
            c.drawString(text_x, text_y, desc)
        
        # (3) Bild zentriert und proportional skalieren
        c.drawImage(
            img_path,
            margin,
            margin + 1.5*cm,
            width=usable_w,
            height=usable_h,
            preserveAspectRatio=True,
            anchor='c',
            mask='auto'
        )
        
                # Parameter für Legende
        bar_thickness  = 0.5 * cm
        legend_length = usable_h * 0.5
        steps = 200
        min_val, max_val = 0.0, 1.0
        text_offset = 0.2 * cm
        
        # Grafikzustand sichern und transformieren
        c.saveState()
        tx = page_w - margin - bar_thickness
        ty = margin
        c.translate(tx, ty)
        c.rotate(90)
        
        # Zustand wiederherstellen
        c.restoreState()
        
        # Farbverlauf zeichnen (Weiß→Gelb→Grün)
        for i in range(steps):
            frac = i / (steps - 1)
            if frac < 0.5:
                r, g = 1, 1
                b    = 1 - 2*frac
            else:
                r    = 2*(1-frac)
                g, b = 1, 0
            x = 0
            y = frac * legend_length
            w = bar_thickness
            h = legend_length / steps
            c.setFillColorRGB(r, g, b)
            c.rect(x, y, w, h, fill=1, stroke=0)
            
        
        # Min/Max-Beschriftung
        c.setFont("Helvetica", 9)
        c.setFillColorRGB(0,0,0)
        c.drawString(bar_thickness + text_offset, 0, f"{min_val:.2f}")
        c.drawString(bar_thickness + text_offset, legend_length - 9,  # annähernd Font-Height
                    f"{max_val:.2f}")
        
        


        c.showPage()
    
    c.save()
    print(f"PDF erstellt: {output_pdf}")