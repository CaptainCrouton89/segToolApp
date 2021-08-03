import json

coco = json.load(open("../test images/processed/annotations.json"))

for annotation in coco["annotations"]:
    segmentation = annotation["segmentation"][0]
    x = segmentation[::2]
    y = segmentation[1::2]
    annotation["bbox"] = [min(x), min(y), max(x)-min(x), max(y)-min(y)]