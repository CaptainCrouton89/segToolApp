from datetime import date

def get_boiler():
    return {
        "info": {
            "year": int(date.today().year),
            "version": "v0.1",
            "description": "Solare panel segmentation data",
            "contributor": "Silas Rhyneer",
            "url": "",
            "date_created": str(date.today()),
        },
        "licenses": {
            "id": 1,
            "name": "no-licence",
            "url": ""
        },
        "categories": [
            {
                "id": 1,
                "name": "pv_cell",
                "supercategory": "pv_cell"
            }
        ],
        "images": [],
        "annotations": []
    }