## **RE Search Aggregator**
### This application will provide an unified portal to prospective and current students to view which colleges and professors wonk under their choice of research field.
#### Version - 0.1
#### Instructions to run:
1. Create a Google App Engine account
2. Create a new project and update the `PROJECT` variable in web-server/app.py and app-tier/app-tier.py
3. Setup [Google cloud sdk](https://cloud.google.com/sdk/docs/quickstart) on your local machine and login 
4. Go to Google Pub/Sub from dashboard
5. Create two topics as given in the values of XXX-topic keys of constants.json file
6. Add a subscription to each topic and name them as given in the values of XXX-sub keys of constants.json file (The topic/subscription combinations are seperated using a new line)
7. Create a new service account key by following [this](https://cloud.google.com/storage/docs/reference/libraries#setting_up_authentication)
8. Download this key in json format and store it inside the .ssh folder (rename it to base-owner-sa.json to match the scripts that we will use to run it)
9. Go to Google Cloud Storage, create a new bucket and upload the constants.json file on it.
10. Note down the bucket-name and update the variable `BUCKET_NAME` in web-server/app.py and app-tier/app-tier.py
11. Install the required python packages from either of the requirements.txt files found in app-tier/ or web-server/
12. Open two terminals and run `./web-server/startWebServer` and `./web-server/startAppTier` scripts (UNIX/MacOS use .sh and Windows use .ps1) 
13. Open localhost:5000 and enter *https://cidse.engineering.asu.edu/faculty/* to test (for now)
14. You should get 74 responses as result if you followed all steps correctly.