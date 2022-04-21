import streamlit as st
import boto3
import uuid

client = boto3.client(
    's3'
)

picture = st.camera_input("Take a picture")
s3bucket = "sales-calls-df-demo"

st.write(f"Take a picture!")

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

