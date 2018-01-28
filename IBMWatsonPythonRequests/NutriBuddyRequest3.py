import json
from watson_developer_cloud import VisualRecognitionV3

visual_recognition = VisualRecognitionV3(
    '2016-05-20',
    api_key='5c962233d2a2dc0672242f5b0e3562e89635f435')

with open('./newRealPicsNutriBuddy.zip', 'rb') as images_file:
    classes = visual_recognition.classify(
        images_file,
        parameters=json.dumps({
            'classifier_ids': ['NutriBuddy3_1205356980'],
            'threshold': 0.6
        })
    )
    print(json.dumps(classes, indent=2))