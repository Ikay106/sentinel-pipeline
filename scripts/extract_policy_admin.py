import os
import pandas as pd 
from googleapiclient.discovery import build
from google.oauth2 import service_account 
import io 
import boto3
from dotenv import load_dotenv
import awswrangler as wr
from datetime import date

load_dotenv()
access =os.getenv('IAM_ACCESS_KEY')
secret =os.getenv('IAM_SECRET_KEY')
region = os.getenv('AWS_REGION')

google_cred = os.getenv('GOOGLE_CREDENTIALS_PATH')
folder_id= os.getenv('GOOGLE_DRIVE_FOLDER_ID')

bucket =os.getenv('S3_LANDING_BUCKET')
print("ACCESS:", repr(access))
print("SECRET:", repr(secret[:8] if secret else None))
try:
    session = boto3.Session(
        aws_access_key_id = access,
        aws_secret_access_key = secret,
        region_name = region
    )
    credentials = service_account.Credentials.from_service_account_file(
        google_cred,
        scopes=['https://www.googleapis.com/auth/drive.readonly']
    )

    drive_service = build('drive', 'v3', credentials=credentials)

    results = drive_service.files().list(
        q=f"'{folder_id}' in parents and mimeType='text/csv'",
        fields="files(id,name)"
    ).execute()

    files = results.get('files',[])
    policy_admin= ["agents.csv","coverages.csv","customers.csv","policies.csv"]
    today = date.today().isoformat()
    source = "policy_admin"

    for file in files:
        if file['name'] not in policy_admin:
            continue
        name= file['name'].replace('.csv','')
        file_id = file['id']

        request = drive_service.files().get_media(fileId=file_id)
        file_content = request.execute()

        df = pd.read_csv(io.BytesIO(file_content))

        wr.s3.to_parquet(
            df=df,
            path= f"s3://{bucket}/source={source}/table={name}/day={today}",
            mode = 'overwrite',
            dataset = True,
            index=False,
            boto3_session= session
        )
        print(f"{name}added succesfully with {df.shape[0]} rows" )

except Exception as e:
    print(e)

finally:
    print("extraction complete")