$env:GOOGLE_APPLICATION_CREDENTIALS="C:\Users\spate100\base-owner-sa.json"
$env:PROJECT=$(gcloud config get-value project)
python ./apptier.py 