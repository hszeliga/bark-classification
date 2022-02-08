#!/usr/bin/env python3 
from flask import Flask, render_template, request, flash
from werkzeug.utils import secure_filename
import os
from azure.storage.blob import BlockBlobService, ContentSettings
import urllib
from PIL import Image
from tensorflow import keras
from keras.preprocessing.image import load_img
from keras.preprocessing.image import img_to_array
from keras.applications.xception import preprocess_input

app = Flask(__name__)
app.secret_key = os.urandom(12)

account_name = 'xxx'  #azure storage account name
account_key = 'xxx' #azure storage account access key  
container = 'xxx' #azure containter name

block_blob_service = BlockBlobService(account_name=account_name, account_key=account_key)

model = keras.models.load_model('model.h5')

species = [
    'Betula alleghaniensis (Yellow Birch)',
    'Betula papyrifera (Paper Birch)',
    'Quercus rubra (Red Oak)', 
    'Picea glauca (White Spruce)', 
    'Picea mariana (Black Spruce)', 
    'Picea abies (Norway Spruce)', 
    'Picea rubens (Red Spruce)', 
    'Acer rubrum (Red Maple)', 
    'Acer saccharum (Sugar Maple)', 
    'Fraxinus americana (White Ash)', 
    'Fagus grandifolia (American Beech)', 
    'Larix laricina (Tamarack)', 
    'Ulmus americana (American Elm)', 
    'Ostrya virginiana (American Hophornbeam)', 
    'Populus tremuloides (Aspen)', 
    'Pinus strobus (Eastern White Pine)', 
    'Pinus resinosa (Red Pine)', 
    'Tsuga canadensis (Eastern Hemlock)', 
    'Abies balsamea (Balsam Fir)', 
    'Thuja occidentalis (White Cedar)'
    ]

def predict(image_path):
    image = load_img(image_path,target_size=(224,224))
    image = img_to_array(image)
    image = image.reshape((1, image.shape[0], image.shape[1], image.shape[2])) 
    image = preprocess_input(image)
    result = model.predict(image)

    results = {}
    for i in range(20):
        results[result[0][i]]=species[i]
    temp=result[0]
    temp=sorted(temp, reverse=True)
    outcome=temp[:3]

    probability=[]
    species_name=[]
    for i in range(3):
        probability.append((outcome[i]*100).round(2))
        species_name.append(results[outcome[i]])    

    return species_name, probability

@app.route('/', methods=['GET'])
def index():
    return render_template("index.html")


@app.route('/', methods=['POST'])        
def bark_classification():
    imagefile=request.files['imagefile']

    if imagefile and imagefile.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        target_image = os.path.join(os.getcwd() , 'static/images')
        filename = secure_filename(imagefile.filename)

        block_blob_service.create_blob_from_stream(container, filename, imagefile)
        settings = ContentSettings(content_type='image/png')
        block_blob_service.set_blob_properties(container, filename, content_settings=settings)
        image_url=f"https://{account_name}.blob.core.windows.net/{container}/{filename}"

        resource = urllib.request.urlopen(image_url)
        temp_filename="temp_img.png"
        image_path = os.path.join(target_image , temp_filename)
        output = open(image_path , "wb")
        output.write(resource.read())
        output.close()
        
        species_name, probability = predict(image_path)

        prediction = {
                      "first_species":species_name[0],
                      "first_probability": probability[0],
                      "second_species":species_name[1],
                      "second_probability": probability[1],
                      "third_species":species_name[2],
                      "third_probability": probability[2],
                    }  

        return render_template("index.html", prediction = prediction, image_url=image_url)
  
    elif imagefile and not imagefile.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        flash('This file cannot be uploaded. Please upload image with one of these extensions: *.png, *.jpg, *.jpeg')
        return render_template("index.html")
    else:
        flash('''Don't be shy, upload something :)''')
        return render_template("index.html")


if __name__ == '__main__':
    app.run()