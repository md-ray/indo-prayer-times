import requests
from datetime import date
from datetime import timedelta

def call_myquran_api(id_city, dt):
    myquran_url = "https://api.myquran.com/v1/sholat/jadwal/" + id_city + "/" + dt
    response = requests.get(myquran_url)
    if (response.status_code == 200):
        print("sukses")
        return response.json()
    else:
        print("tidak sukses")
        return None

# Extract Dates
today = date.today()
tomorrow = date.today() + timedelta(days=1)
dt_today = today.strftime("%Y/%m/%d")
dt_tomorrow = tomorrow.strftime("%Y/%m/%d")

# Init variables
jadwal_today = {}
jadwal_tomorrow = {}

return_json = call_myquran_api("1108", dt_tomorrow)
if (return_json != None):
    # print(return_json)
    # print("Jadwal Maghrib: " + return_json["data"])
    jadwal_today = return_json["data"]["jadwal"]
    print(jadwal_today)
