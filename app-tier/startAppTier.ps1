$env:GOOGLE_APPLICATION_CREDENTIALS="$HOME\.ssh\base-owner-sa.json"
$env:PROJECT=$(gcloud config get-value project)
python ./apptier.py 