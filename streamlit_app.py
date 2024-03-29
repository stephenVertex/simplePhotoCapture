import streamlit as st
import boto3
import uuid
import time
from collections import OrderedDict
import os
import json
import pandas as pd
import re

import datetime

from streamlit_cookies_manager import EncryptedCookieManager

# This should be on top of your script
cookies = EncryptedCookieManager(
    # This prefix will get added to all your cookie names.
    # This way you can run your app on Streamlit Cloud without cookie name clashes with other apps.
    prefix="ktosiek/streamlit-cookies-manager/",
    # You should really setup a long COOKIES_PASSWORD secret if you're running on Streamlit Cloud.
    password=os.environ.get("COOKIES_PASSWORD", "My secret password"),
)
if not cookies.ready():
    # Wait for the component to load and send us current cookies.
    st.stop()

st.write("Current cookies:", cookies)



cookie="aurea1-demo-id"
if cookie not in cookies:
    cookies[cookie] = str(uuid.uuid4()) + "--aurea1-demo"
    cookies.save()


client = boto3.client(
    's3'
)

## The main interface. 
## Prompt for taking a picture
picture = st.camera_input("Take a picture")
s3bucket = "geneva-devflows-2022-demo"
st.write(f"Take a picture")
st.write(f"Or, upload one")
uploaded_file = st.file_uploader(
    label="Upload an image", 
    type=['.png', '.jpg', '.jpeg'], 
    accept_multiple_files=False, 
    key=None, help=None, 
    on_change=None,
    label_visibility="visible")

## If given an input photo name
##    A) new_key = "input/thing.image"
##    B) Once the analysis runs, then we expect to also have
##       nk2 = new_key + "--label-data.json"
##    C) If we have new_key and nk2 then proceed
##    D) Download
def getPhotoInfo(new_key = None):

    session = boto3.Session()

    s3bucket = "geneva-devflows-2022-demo"
    prefix = "rekognition/general/" + cookies[cookie]

    #st.write(f"{prefix=}")

    s3 = session.resource('s3')
    my_bucket = s3.Bucket(s3bucket)

    ## Query the list of files in S3
    object_list = []
    for i in my_bucket.objects.filter(Prefix=prefix):
        object_list.append(i)

    ## Sort them by last modified
    ## DONE here would be a good place to search for the "*--label-data.json" extension
    sorted_objects = sorted(object_list, key= lambda x: x.last_modified, reverse=True)
    s2 = list( filter(lambda x: re.match(".*--label-data.json$", x.key), sorted_objects)   )    
    top5 = s2[0:5]

    if new_key is not None:
        ## DONE Need to fix this, as we now have them in the same bucket
        ## it should be something like
        nk2 = new_key + "--label-data.json"

        ## TODO Add the check for the new lmage as well
        key_list = [x.key for x in top5]
        print(f"Looking for {nk2} in {key_list}")
        if nk2 not in key_list:
            return(False)

    ## Download the json files if we don't have them already
    labels = OrderedDict()
    namesdict = OrderedDict()
    json_urls = []
    for t in top5:
        fname = "/tmp/" + t.key
        print(fname)
        base = os.path.split(t.key)[0]
        os.makedirs(os.path.join("/tmp" ,base), exist_ok=True)
        my_bucket.download_file(t.key, fname)
        json_urls.append(f"https://{s3bucket}.s3.amazonaws.com/" + t.key)
        print("...DONE")
        with open(fname, "r") as f:
            labels[t.key] = json.loads(f.read()) #['label_data']
            namesdict[t.key] = labels[t.key]['label_data']

    #st.write(f"DEBUG: labels - {labels}")

    ## Get the labels
    namesInPic = OrderedDict()
    for k,v in namesdict.items():
        try:
            names = [f"{x['Name']}, {x['Score']:.2f}" for x in v]
        except TypeError as e:
            raise TypeError(f"ERROR: parsing name and scores from {v}") from e
        namesInPic[k]=names

    taggedUrls = OrderedDict()
    for k,v in labels.items():
        #print(v)
        #if type(v) == list:
            ## This is an error case in which I accidently
            ## pass in the inner object
            #names = [f"{x['Name']}, {x['Score']:.2f}" for x in v]
            #scores = [x['Score'] for x in v]
        #elif 'Labels' in v.keys():
        #    names = [x['Name'] for x in v['Labels']]
        #    print(names)
        #elif 'Name' in v.keys():
        #    names = [v['Name']]
        #else:
        #    names = ["No names"]
            #scores = ["No scores"]
        #namesInPic[k] = names
        #scoresInPic[k] = scores

        if 'bounded_image' in v.keys():
            taggedUrls[k] = v['bounded_image']
        else:
            taggedUrls[k] = "Error"

    ## Generate the URLS
    picUrls = OrderedDict()
    for t in top5:
        k = t.key
        ## TODO Fix the image url generator by stripping "--label-data.json"
        ## and then adding the right thing
        imgid = k.replace("--label-data.json", "")
        imgurl = f"https://{s3bucket}.s3.amazonaws.com/" + imgid
        picUrls[k] = imgurl

    def newLineList(x):
        return("<br>".join(x))

    def mkImageTag(x):
        return(f"<img width=\"200\" src=\"{x}\"/>")

    df = pd.DataFrame({
        'time'   : [str(x.last_modified) for x in top5],
        #'labels' : [str(uploaded_file = st.file_uploader("Choose a file")
        #'labels' : [str(x) for x in list(namesInPic.values())],
        'labels' : [newLineList(x) for x in list(namesInPic.values())],
        #'confidence' : [newLineList(str(x)) for x in list(scoresInPic.values())],
        #'url'    : list(picUrls.values())
        #'Image'    : [mkImageTag(x) for x in picUrls.values()],
        'Labeled Image'  : [mkImageTag(x) for x in taggedUrls.values()],
        'JSON' : [str(x) for x in json_urls]
    })

    print(df)
    # st.write(df)
    st.write(df.to_html(escape=False), unsafe_allow_html=True)
    return(True)

if picture:
    ukey = str(uuid.uuid4())
    ## TODO parameterize the "flowers" part somehow
    ## This is where we decide where to put it
    ## We can make a folder called GENERAL which has this.
    s3key = "rekognition/general/" + cookies[cookie] + "/" + ukey + ".jpg"
    fname = "/tmp/" + ukey + ".jpg"
    ## Write image to temp file
    f = open(fname, 'wb')
    f.write(picture.getvalue())
    f.close()

    ## Show the user, and tell them what happened
    st.image(picture)

    ## Upload the file
    client.upload_file(fname, s3bucket, s3key)
    st.write(f"Uploaded {s3key} to {s3bucket}")

    ## Sleep for 5 seconds to give the thing time
    r = getPhotoInfo(s3key)
    tries = 0
    while(r is False and tries < 100):
        print(f"{tries} : We don't have it yet. Sleeping")
        time.sleep(1)
        r = getPhotoInfo(s3key)
        print(f"\t{r}")
        tries = tries + 1

elif uploaded_file:
    ukey = str(uuid.uuid4())
    s3key = "rekognition/general/" + cookies[cookie] + "/" + ukey + ".jpg"
    fname = "/tmp/" + ukey + ".jpg"
    ## Write image to temp file
    f = open(fname, 'wb')
    f.write(uploaded_file.getvalue())
    f.close()

    ## Show the user, and tell them what happened
    st.image(uploaded_file)

    ## Upload the file
    client.upload_file(fname, s3bucket, s3key)
    st.write(f"Uploaded {s3key} to {s3bucket}")

    ## Sleep for 5 seconds to give the thing time
    r = getPhotoInfo(s3key)
    tries = 0
    while(r is False and tries < 100):
        print(f"{tries} : We don't have it yet. Sleeping")
        time.sleep(1)
        r = getPhotoInfo(s3key)
        print(f"\t{r}")
        tries = tries + 1
else:
    getPhotoInfo()
