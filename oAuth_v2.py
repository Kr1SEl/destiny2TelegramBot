import requests
import os
from dotenv import load_dotenv
import json
import urllib


def getDataForToken(token: str):
    return f'grant_type=refresh_token&client_id=39654&refresh_token={urllib.parse.quote(token.encode("utf-8"), safe="")}'


def getToken(requestToken: str):
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-API-Key': os.getenv('D2TOKEN'),
        'Authorization': os.getenv('AUTHORIZATION')
    }
    response = requests.post(
        os.getenv('TOKEN_URL'), data=getDataForToken(requestToken), headers=headers)
    requestToken = response.json()['refresh_token']
    print(response.json())


def run():
    requestToken = 'CP6HBBKGAgAgcHFvmpslmwlJRweOE+1Bc09LvseSc8tr6HqIqQxfk27gAAAArKkJq3DKI/JxbMXfza64b8BEhqaWrV4l5dP67u0WDR4EFDPAvOFuYXg5wzveBmAVipPCKTiUfoWfGuxaGeUEJOPInMDvOsGQX63lm0LD6+JuughRSKzaJr/u/CrQNlUoW2Ytoxr0s9sR7UaxdU2xgWTULFubhdhSN9rRhCJLIV0WqMoXw9bjHZtr482ExVyG/pf26hFpHWRvWtLStLpK9syMAc1JLF4JfEbs2Wmlv8oYFcGLCZoiHn4cinVbDJjZByynBNgjfCXfc62yrelCCREWF7oh6wcLd+LOcQmiCKs='
    load_dotenv()
    getToken(requestToken)


run()
