import os
from dotenv import load_dotenv
import boto3
import json
from googleapiclient.discovery import build
from google.oauth2 import service_account 

load_dotenv()
access =os.getenv('IAM_ACCESS_KEY')
secret =os.getenv('IAM_SECRET_KEY')
region = os.getenv('AWS_REGION')

google_cred = os.getenv('GOOGLE_CREDENTIALS_PATH')
folder_id= os.getenv('CLAIMS_FOLDER_ID')
bucket =os.getenv('S3_LANDING_BUCKET')

try:
    session = boto3.Session(
            aws_access_key_id = access,
            aws_secret_access_key = secret,
            region_name = region
        )
    s3_client = session.client('s3')
    
    credentials = service_account.Credentials.from_service_account_file(
        google_cred,
        scopes=['https://www.googleapis.com/auth/drive.readonly']
    )

    drive_service = build('drive', 'v3', credentials=credentials)

    results= drive_service.files().list(
        q=f"'{folder_id}' in parents and mimeType ='application/vnd.google-apps.folder'",
        fields="files(id,name)"
    ).execute()

    folders = results.get('files',[])
    today = date.today().isoformat()
    source="claims_mgmt"

    for folder in folders:
        file_id = folder['id']
        file_list= drive_service.files().list(
            q=f"'{file_id}' in parents and mimeType='application/json'",
            fields="files(id,name)"
        ).execute()

        folder_name=folder['name']
        files =file_list.get('files',[])
        initialCount=0

        for file in files:
            name = file['name']
            id = file['id']
            key = f"source={source}/{folder_name}/{name}"
            
            #check if file exists
            try:
                s3_client.head_object(Bucket=bucket, Key=key)
                print(f"{name} already exists, skipping")
                continue
            except:
                pass

            file_content = drive_service.files().get_media(fileId=id).execute()
            s3_client.put_object(
                Bucket=bucket,
                Key=key,
                Body=file_content
            )
            print(f"{name} has been added to {bucket}")
            initialCount += 1
        print(f"{initialCount} files were uploaded in {folder_name}")

except Exception as e:
    print(e)

finally:
    print("upload complete")