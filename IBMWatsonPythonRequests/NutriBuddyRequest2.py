import json
from watson_developer_cloud import VisualRecognitionV3

visual_recognition = VisualRecognitionV3(
    '2016-05-20',
    api_key='5aebbb8a60e0c8e2c489c3542a6b462de6bde68d')

with open('./newRealPicsNutriBuddy.zip', 'rb') as images_file:
    classes = visual_recognition.classify(
        images_file,
        parameters=json.dumps({
            'classifier_ids': ['NutriBuddy2_2068441055'],
            'threshold': 0.6
        })
    )
    print(json.dumps(classes, indent=2))