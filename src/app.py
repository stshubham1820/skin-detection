from __future__ import division, print_function
import sys
import os
import glob
import re
from pathlib import Path
from io import BytesIO
import base64
import requests
# Import fast.ai Library
from fastai import *
from fastai.vision import *
import mysql.connector
from werkzeug.utils import secure_filename
from flask import Flask, redirect, url_for, render_template, request
from PIL import Image as PILImage
import googlemaps
import pandas
current_location = os.path.dirname(os.path.abspath(__file__))
# Define a flask app
app = Flask(__name__)

NAME_OF_FILE = 'model_best' # Name of your exported file
PATH_TO_MODELS_DIR = Path('') # by default just use /models in root dir
classes = ['Actinic keratoses', 'Basal cell carcinoma', 'Benign keratosis',
           'Dermatofibroma', 'Melanocytic nevi', 'Melanoma', 'Vascular lesions']

def setup_model_pth(path_to_pth_file, learner_name_to_load, classes):
    data = ImageDataBunch.single_from_classes(
        path_to_pth_file, classes, ds_tfms=get_transforms(), size=224).normalize(imagenet_stats)
    learn = cnn_learner(data, models.densenet169, model_dir='models')
    learn.load(learner_name_to_load, device=torch.device('cpu'))
    return learn

learn = setup_model_pth(PATH_TO_MODELS_DIR, NAME_OF_FILE, classes)

def encode(img):
    img = (image2np(img.data) * 255).astype('uint8')
    pil_img = PILImage.fromarray(img)
    buff = BytesIO()
    pil_img.save(buff, format="JPEG")
    return [base64.b64encode(buff.getvalue()).decode("utf-8"),img]
	
def model_predict(img,name,username,getimg=''):
    Img = getimg
    img = open_image(BytesIO(img))
    pred_class,pred_idx,outputs = learn.predict(img)
    formatted_outputs = ["{:.1f}%".format(value) for value in [x * 100 for x in torch.nn.functional.softmax(outputs, dim=0)]]
    pred_probs = sorted(
            zip(learn.data.classes, map(str, formatted_outputs)),
            key=lambda p: p[1],
            reverse=True
        )
	
    img_data = encode(img)
    result = {"class":pred_class, "probs":pred_probs, "image":img_data[0]}
    print(pred_class)
    if Img =='':
        return render_template('result.html', result=result,Name=name,message="With Url Image We Can't Store Your History ! Thankyou For Using Our Service")
    else :
        qry = 'Insert into Image Set user_id=(Select username from User where username=%s),image=%s,prediction=%s,img=%s'
        print(pred_class)
        print(len(img_data[0]))
        pointer.execute(qry,(username,Img,str(pred_class),img_data[0]))
        mydb.commit()
        return render_template('result.html', result=result,Name=name,var='none')

try :
    mydb = mysql.connector.connect(
            host='muskan-db.cd4i7wkmxrec.ap-south-1.rds.amazonaws.com',
            user='admin', 
            password = "Stshubham",
            db = 'user'
            )
    pointer = mydb.cursor()  
except Exception as err:
    Err = str(err).split(" '")[0].split(": ")[1]
    if Err == 'Unknown MySQL server host':
        print('Please Check Your Internet Connection')
    else :
        print(Err)
def check(username,password):
    querry = 'Select username,password,name from User where username=%s AND password=%s'
    pointer.execute(querry,(username,password))
    data = pointer.fetchone()
    if data:
        return data
    else :
        return ''
@app.route('/')
def index():
    # Main page
    return render_template('login.html',var='none')

@app.route('/register', methods=["POST"])
def register():
    Name = request.form['name']
    Username = request.form['username']
    Password = request.form['password']
    print(Username,Password)
    get = check(Username,Password)
    if len(get) != 0 :
        return redirect('/')
    else :
        querry = 'Insert into User (username,password,name) values (%s,%s,%s)'
        pointer.execute(querry,(Username,Password,Name))
        mydb.commit()
        return redirect('/')

@app.route('/', methods=["POST"])
def checklogin():
    username = (request.form['username'])
    password = request.form['password']
    get = check(username,password)
    print(username,password)
    if len(get) != 0:
        Name = get[2]
        return render_template('index.html',Name=Name,username=username)
    else :
        return render_template('login.html',status='Please Check Your Credentials',clr='danger')
        #url_for('user_page', name = username)

@app.route('/upload', methods=["POST", "GET"])
def upload():
    if request.method == 'POST':
        # Get the file from post request
        getimg = request.files['file']
        img = request.files['file'].read()
        name = request.form["name"]
        print(getimg)
        username = request.form["username"]

        filename = secure_filename(getimg.filename)
        if img != None:
        # Make prediction
            preds = model_predict(img,name,username,filename)
            return preds
    return 'OK'
	
@app.route("/classify-url", methods=["POST", "GET"])
def classify_url():
    if request.method == 'POST':
        url = request.form["url"]
        name = request.form["name"]
        username = request.form["username"]
        if url != None:
            response = requests.get(url)
            preds = model_predict(response.content,name,username)
            return preds
    return 'OK'

@app.route("/history",methods=["POST"]) 
def history():
    name = request.form["name"]
    username =  request.form["username"]
    querry = 'select * from Image where user_id=%s'
    pointer.execute(querry,(username,))
    data = pointer.fetchall()
    return render_template('history.html',Name=name,username=username,Data=data,var=1)
if __name__ == '__main__':
    port = os.environ.get('PORT', 8008)

    if "prepare" not in sys.argv:
        app.run(debug=True, host='0.0.0.0', port=port)
