import requests
from bs4 import BeautifulSoup

# URL for the GET and POST requests
url = "https://green2.kingcounty.gov/lake-buoy/Data.aspx"

# Start a session
session = requests.Session()

# Initial GET request to fetch the form
initial_response = session.get(url)
soup = BeautifulSoup(initial_response.content, 'html.parser')

# Extract all hidden form fields
form_data = {}
for hidden_input in soup.find_all("input", type="hidden"):
    form_data[hidden_input['name']] = hidden_input['value']

# Manually set necessary fields for the form submission
form_data.update({
    "__EVENTTARGET": "",
    "__EVENTARGUMENT": "",
    "__LASTFOCUS": "",
    "__VIEWSTATE": "UOW6Z4RhVN1IR3v5lY1+cM5ZGTFk0db+fdKOTa1ZeHQ3zqFakVQ1h2W3bWowBRcZLlIG95tmqBv4QkuopxHtt1LzHQ5PvSfo3wD0qkj6gRfUNukfAUKiHfFRWrQacJxwSHZXSJud9KJ72AoV0ZwcmmNF/TUIfFtYuabFUBrBu9tFw6u4tnc657K6g1KbqE86tFIho0WTb9tX+iYGAgF9tpCMq7kg6yd4fnDuDqdOMA+80EOeJm7VZJB666i80lMTQM6pCBEVRD4+8d3VU6RgEm2PL3dc+xBP0JvJA9QAwM3VsgncObO9jU0SB3qzbQ9QU3kf8P5DbKLZAhVSifVY2QlixBy0fs2t6mXda77tv0y7cHG2TYqAh16Z09PtL82WgcZt3oDXbWF7rHHhVNLvLMQXRpXpkk4FR+POTca8kmGrZD55TYLUyTL3/03c5ijf24SzPOlB6DuWT+DfZB9eOboyYMh1cUyOj2ceOrjZC38n3IgQGw2CKA30Vx3dRIFhegIkCpToz+OydYRU+7ukZkZAqm4cIzw6t9MJ9S44dWAVqDE+LYYPV+QjPxq7tjHDUbU8b0r8BS/Ggu1W7m9wLyoP6LiH0ifEuiVtHKt6hpmmr1u399xE0CbK64xYpWHPXgXBm5zKq97nre2GoJHg6kL7XHwFqaLc93ppVdPebSWPr1KnC570tu2hmHYjYi+u6B1e81KYtZh67SjfNJZ5Igx/YqQ7f8qcd1Sv5LpynejanK/8IkE4b/xUpflR17rm6zjiSnKgU6z4x7mq2srW0nVgxsZyRqV89AkseOEQTnpgMVMV/aIw8Vh2lJpE6Nu02zCAkWaBPC9Nz0WnVDRsfu5cbIVKenfA/2w34J3SITFurNyG4RBw2u4kqdnxndaOQ3k6KEvZgBd+IpSVoH9VGqToH4ELe8ZF5/wk3/7FRdqILxFt65rSnt6jgoscaSi+iCnXIFB56Rxxfz3GIBrS6WHM8Fn8WrlXE0WvfXr3dsWz2lv+vDMIXkzZqPVP7dU1VoA/fdorNRnSpEhc90i5ahmx4DDGxYpqMnh+Ft5NHHXV9gDaCXMl83QpgmyKCKHK",
    "__VIEWSTATEGENERATOR": "7A1DE6B6",
    "__VIEWSTATEENCRYPTED": "",
    "__EVENTVALIDATION": "oKy3se0hmOJVU3IFj6aeoCUYhixoRNxFTbJWyP7CrHX7toRzKgLEjTofpKs+SLRjdzHN8oj15W8iw2aWWs4LKtJM1MMC1v/Ivo3b3ohub4VCy7d9DBipIBmfmRz59QwJfl1ckRF6yeiYBhq3g59fQb2+hjqXPKAf+/J8JS4/+lAnSqaK1mgrxjrzWKr7lj1VLBChc4k3Im7BK22cagYvik6UghRJpHS5jFk6Xr0PsHIq4kipOvknmkhqAwxAainwsU0ygtNNmA82lhm/mYm1ihBs3AjbxHsQfOGrUWd0IM2k+1W/BAosrqWB8VbJUupbCo3fRkXoYFIiRTg6aMmCvOppdyN4u1XfqoLYQsfTEWWGG5oUxWK8rRsBYDj/9/C+tnHPnEFnXzrKjElh8lEBcN37+ePndV0+9Ieeju/I8VR+3nRJR9sd0/xk2Y9E0Ajij1pUsEOAoYmgWOVj8aX37xsbYf+5LeCuaM8GSSQ1AGc4N7KozquCeBjiUbq+tgTM2ikMk989ZbXTSNf1zSxXNxQknP3RWOwYPf6/K5LAxO4z03+ZGLuH2WyGHq2m0robJLfWr1J5FQ9IvfMgiCjKuMwfoZd7l/A/BwFXBBzD3FXc2HiWcfsddij7wpnfzw/BwrWI79vswatHSyRXpleXJqUl0Gbd12/Sq2Zf0aEwYoemnSDT2oUJw7EQcwOaOhzz2JFgjWs00Hr0xm+LlDBoUs6lhgNFHpzLSroM+SL6p3KEiW/FvrVO3Sjcd6myCH8GSWnJ9s2PrJQ9U6S3Zt6xLaXT9+i0Vg6EUuBPPMbFdmLH0KAXGRBsvqYG5sZxqJpwls4ODVTTphy63TCEoJtrvotiq3WrUfa2zXlogmJfN8IXwFWVbTMJp1AoriOy9aBEKHLWHFIKNizyQlyfSFjdBCckKe1DIZKaG1JGXbtovXbkjF5bkrYF8rtTUH3vMLCBQ1VilEKuDW7cjrNmn8IlL5CJzlUWvs0f8FZTnkWZ+0g1dNdkZAW33p7G1/pFkdYn0j6E1kytS14MtdHdiQJ7IlIXGZJ6lKLLQBrPTV/97QmuCC5LL7X6f0drG5s1GBN2wHaIDrpW5uqb6XY8otTsQbf8yG2mrGIS2woFU71tAkSdCSvDHr4kz8p0zwek3QToz8azrTkmbrf+0j1bSV/xOmUfQSZcpkf5KeOfa4Ycy06lCHGmllVcbS0ZTCsIg2KtG/Vmmd6aIrrBWXETEQfMLnWX88GZEidlncCkRDg3K8DLGK1PczKGLNNQHnOoflbPYSs0bkdiQ0J4n4fjL9MEaM1cz8Tv/g9MB7DezjvoZLRRsssbBWzqVzUzU+PWAIUExJb+7KJskozq/D+rE37PMUNnpKack3bWQnkJCd71VbBPCY1oRcb0OgVq2/ox3NLPNpERd0wUOqrM/zvU/UR1DxuIUOjo6U0VMlv2b5qeBZJH9ZARMWlugOtX1f1By1x6",
    "ctl00$kcMasterPagePlaceHolder$c_TypeDropDownList": "Profile",
    "ctl00$kcMasterPagePlaceHolder$c_BuoyDropDownList": "Sammamish",
    "ctl00$kcMasterPagePlaceHolder$c_YearDropDownList": "2025",
    "ctl00$kcMasterPagePlaceHolder$c_MonthStartDropDownList": "9",
    "ctl00$kcMasterPagePlaceHolder$c_EndMonthDropDownList": "9",
    "ctl00$kcMasterPagePlaceHolder$c_DownloadButton": "Download"
})

# Headers for the POST request
headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Content-Type": "application/x-www-form-urlencoded",
    "Cookie": "; ".join([f"{key}={value}" for key, value in session.cookies.get_dict().items()]),
    "Host": "green2.kingcounty.gov",
    "Origin": "https://green2.kingcounty.gov",
    "Referer": "https://green2.kingcounty.gov/lake-buoy/Data.aspx",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "sec-ch-ua": "\"Google Chrome\";v=\"125\", \"Chromium\";v=\"125\", \"Not.A/Brand\";v=\"24\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"macOS\""
}

# Send the POST request
response = session.post(url, headers=headers, data=form_data)

# Check if the response contains the expected content
if "application/x-msdownload" in response.headers.get("Content-Type", ""):
    # Save the response content as a tab-delimited text file
    txt_file_path = "SammamishProfile.txt"
    with open(txt_file_path, "wb") as file:
        file.write(response.content)
    print("Data downloaded and saved as SammamishProfile.txt successfully.")
else:
    print("Failed to download data. The response does not contain the expected file.")
    print("Response Status Code:", response.status_code)
    print("Response Headers:", response.headers)
    print("Response Content:", response.text[:1000])  # Print first 1000 characters for inspection

# Save the full response content to a file for inspection
with open("response_content.html", "w", encoding="utf-8") as file:
    file.write(response.text)

