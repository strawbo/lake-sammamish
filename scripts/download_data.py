import requests
import datetime

def download_data():
    today = datetime.date.today()
    url = f"https://example.com/data?year={today.year}&month={today.month}"  # Update with actual API
    response = requests.get(url)

    if response.status_code == 200:
        with open("SammamishProfile.txt", "w") as file:
            file.write(response.text)
        print("Download successful!")
    else:
        print("Download failed!")

download_data()

