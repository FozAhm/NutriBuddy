import json
from watson_developer_cloud import VisualRecognitionV3

visual_recognition = VisualRecognitionV3(
    '2016-05-20',
    api_key='4dca49e7ed0f66d48199e83d4faf0509e1c16e4a')

with open('./newRealPicsNutriBuddy.zip', 'rb') as images_file:
    classes = visual_recognition.classify(
        images_file,
        parameters=json.dumps({
            'classifier_ids': ['NutriBuddy_1477767040'],
            'threshold': 0.1
        })
    )
print(json.dumps(classes, indent=2))
