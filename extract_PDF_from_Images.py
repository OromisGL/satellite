from utils import images_to_pdf
import os
import glob

image_folder = 'Images'

image_paths = sorted(glob.glob(os.path.join(image_folder, "German_NDVI_*.png")))

list_year = [2018, 2019, 2020, 2021, 2022, 2023, 2024]
index = -1
text = {}
for i in range(len(image_paths)):
    text.update({os.path.splitext(os.path.basename(image_paths[i]))[0]: f'Germany September {list_year[i]} NDVI'})
    # PDF erzeugen
    
images_to_pdf(
        image_folder="Images",
        output_pdf="German_NDVI_Report.pdf",
        descriptions=text,
        common_prefix='German_NDVI_'
    )