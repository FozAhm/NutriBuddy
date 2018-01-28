import json
from watson_developer_cloud import VisualRecognitionV3

visual_recognition = VisualRecognitionV3(
    '2016-05-20',
    api_key='b951be200485891f5af6c728e782af750870cfea')

with open('./newRealPicsNutriBuddy.zip', 'rb') as images_file:
    classes = visual_recognition.classify(
        images_file,
        parameters=json.dumps({
            'classifier_ids': ['NutriBuddy4_1216984207'],
            'threshold': 0.6
        })
    )
    print(json.dumps(classes, indent=2))