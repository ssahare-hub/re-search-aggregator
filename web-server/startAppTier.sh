export GOOGLE_APPLICATION_CREDENTIALS= ~\.ssh\base-owner-sa.json
export PROJECT=gcloud config get-value project
python ../app-tier/apptier.py