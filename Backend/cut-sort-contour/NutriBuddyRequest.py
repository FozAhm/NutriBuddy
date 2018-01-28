import json
from watson_developer_cloud import VisualRecognitionV3
import reg_green

def watsonRequest(path , key, classifier):  #path to be properly escaped (\\)

    visual_recognition = VisualRecognitionV3(
        '2016-05-20',
        api_key=key)

    with open(path, 'rb') as images_file:
        classes = visual_recognition.classify(
            images_file,
            parameters=json.dumps({
                'classifier_ids': [classifier],
                'threshold': 0.6
            })
        )
        if classes['images'][0]['classifiers'][0]['classes'][0]['class'] == "banana" or \
            classes['images'][0]['classifiers'][0]['classes'][0]['class'] ==  "tomato" or \
            classes['images'][0]['classifiers'][0]['classes'][0]['class'] == "broccoli":
            reg_green.green(path, classes['images'][0]['classifiers'][0]['classes'][0]['class'])
        elif  classes['images'][0]['classifiers'][0]['classes'][0]['class'] == "cola" or\
            classes['images'][0]['classifiers'][0]['classes'][0]['class'] ==  "candy":
            reg_green.red(path, classes['images'][0]['classifiers'][0]['classes'][0]['class'])

