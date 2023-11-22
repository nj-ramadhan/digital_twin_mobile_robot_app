
import requests

try :
    r = requests.get('https://app.kickyourplast.com/api/' + 'transaction_by_code/' + '6ZDJXMTJC')
    print(r.json()['transaction_details'][0]["size"])

except Exception as e:
    print(e)