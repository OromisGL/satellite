from utils import images_to_pdf
import os
import glob

image_folder = 'Images'

image_paths = sorted(glob.glob(os.path.join(image_folder, "German_NDVI_*.png")))

text = [
    'Germany September 2018',
    'Germany September 2019',
    'Germany September 2020',
    'Germany September 2021',
    'Germany September 2022',
    'Germany September 2023',
    'Germany September 2024'
]


for image_path in image_paths:
    basenames = [basename for basename in os.path.splitext(os.path.basename(image_path))[0]]


descriptions = {(basename for basename in basenames): tex for tex in text}
    # PDF erzeugen
images_to_pdf(
        image_folder="Images",
        output_pdf="German_NDVI_Report.pdf",
        descriptions=descriptions
    )