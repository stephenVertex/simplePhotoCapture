import streamlit as st
import boto3
import uuid
import time
from collections import OrderedDict
import os
import json
import pandas as pd
client = boto3.client(
    's3'
)

picture = st.camera_input("Take a picture")
s3bucket = "sales-calls-df-demo"

st.write(f"Take a picture!")

def getPhotoInfo(new_key = None):

    session = boto3.Session()

    s3bucket = "sales-calls-df-demo"
    prefix = "inboundimageslabelling/"

    s3 = session.resource('s3')
    my_bucket = s3.Bucket(s3bucket)

    ## Query the list of files in S3
    object_list = []
    for i in my_bucket.objects.filter(Prefix=prefix):
        object_list.append(i)

    ## Sort them by last modified
    sorted_objects = sorted(object_list, key= lambda x: x.last_modified, reverse=True)
    top5 = sorted_objects[0:5]

    if new_key is not None:
        nk2 = new_key.replace(".jpg", ".json").replace("inboundimages", "inboundimageslabelling")
        key_list = [x.key for x in top5]
        print(f"Looking for {nk2} in {key_list}")
        if nk2 not in key_list:
            return(False)

    ## Download the json files if we don't have them already
    labels = OrderedDict()
    for t in top5:
        fname = "/tmp/" + t.key
        print(fname)
        base = os.path.split(t.key)[0]
        os.makedirs(os.path.join("/tmp" ,base), exist_ok=True)
        my_bucket.download_file(t.key, fname)
        print("...DONE")
        with open(fname, "r") as f:
            labels[t.key] = json.loads(f.read())


    ## Get the labels
    namesInPic = OrderedDict()
    for k,v in labels.items():
        names = [x['Name'] for x in v['Labels']]
        print(names)
        namesInPic[k] = names

    ## Generate the URLS
    picUrls = OrderedDict()
    for t in top5:
        k = t.key
        imgid = os.path.splitext(os.path.split(k)[1])[0]
        imgurl = f"https://sales-calls-df-demo.s3.amazonaws.com/inboundimages/{imgid}.jpg"
        picUrls[k] = imgurl

    def newLineList(x):
        return("<br>".join(x))

    def mkImageTag(x):
        return(f"<img width=\"200\" src=\"{x}\"/>")

    df = pd.DataFrame({
        'time'   : [str(x.last_modified) for x in top5],
        #'labels' : [str(x) for x in namesInPic.values()],
        #'labels' : [str(x) for x in list(namesInPic.values())],
        'labels' : [newLineList(x) for x in list(namesInPic.values())],
        #'url'    : list(picUrls.values())
        'url'    : [mkImageTag(x) for x in picUrls.values()]
    })

    print(df)
    # st.write(df)
    st.write(df.to_html(escape=False), unsafe_allow_html=True)
    return(True)

if picture:
    ukey = str(uuid.uuid4())
    s3key = "inboundimages/" + ukey + ".jpg"
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
    while(r is False and tries < 20):
        print(f"{tries} : We don't have it yet. Sleeping")
        time.sleep(1)
        r = getPhotoInfo(s3key)
        print(f"\t{r}")
        tries = tries + 1
    
else:
    getPhotoInfo()
