## **RE Search Aggregator**
### This application will provide an unified portal to prospective and current students to view which colleges and professors work under their choice of research field.
#### Version - 0.1
#### Instructions to run:
1. Create a **Google App Engine** account
2. Create a **new project** and update the `PROJECT` variable in *web-server/app.py* and *app-tier/app-tier.py*
3. Setup [Google cloud sdk](https://cloud.google.com/sdk/docs/quickstart) on your local machine and login 
4. Go to **Google Pub/Sub** from dashboard
5. Create two **topics** as given in the values of *XXX-topic keys of constants.json* file
6. Add a **subscription** to each topic and name them as given in the values of *XXX-sub keys of constants.json* file (The topic/subscription combinations are seperated using a new line)
7. Create a new **service account key** by following [these steps](https://cloud.google.com/storage/docs/reference/libraries#setting_up_authentication)
8. Download this key in **json format** and store it inside the *.ssh* (rename it to base-owner-sa.json to match the scripts that we will use to run it). !! This file can be inside any folder, just make sure to update `startWebServer` and `startAppTier` scripts 
9. Go to **Google DataStore** and enable it then go to **Google Cloud Storage**, create a **new bucket** and *upload the constants.json file on* it.
10. Note down the bucket-name and update the variable `BUCKET_NAME` in web-server/app.py and app-tier/app-tier.py
11. Install the required python packages from either of the requirements.txt files found in app-tier/ or web-server/
12. OS Specific installation for ``pdftotext python library ->
    - Debian, Ubuntu, and friends
      - sudo apt install build-essential libpoppler-cpp-dev pkg-config python3-dev
    - Fedora, Red Hat, and friends
      - sudo yum install gcc-c++ pkgconfig poppler-cpp-devel python3-devel
    - macOS
      - brew install pkg-config poppler python
    - Windows
      - Currently tested only when using conda:
        - Install the Microsoft Visual C++ Build Tools 14.0.0
        - Install poppler through conda:
          - conda install -c conda-forge poppler
13. Open two terminals, cd into each directory ` cd ./web-server` and run `./startWebServer.{your extension}` and similarly `cd ./app-tier` and run `.\startAppTier.{your extension}` scripts (Ubuntu/Linux/MacOS use .sh and Windows use .ps1) 
14. Open *localhost:5000* and enter *https://cidse.engineering.asu.edu/faculty/* to test (for now)
15. You won't get anything on the front end, but you should see processing happening on the terminal. 