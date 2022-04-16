import requests
import config
import json
import urllib

requestToken = 'CP6HBBKGAgAgcHFvmpslmwlJRweOE+1Bc09LvseSc8tr6HqIqQxfk27gAAAArKkJq3DKI/JxbMXfza64b8BEhqaWrV4l5dP67u0WDR4EFDPAvOFuYXg5wzveBmAVipPCKTiUfoWfGuxaGeUEJOPInMDvOsGQX63lm0LD6+JuughRSKzaJr/u/CrQNlUoW2Ytoxr0s9sR7UaxdU2xgWTULFubhdhSN9rRhCJLIV0WqMoXw9bjHZtr482ExVyG/pf26hFpHWRvWtLStLpK9syMAc1JLF4JfEbs2Wmlv8oYFcGLCZoiHn4cinVbDJjZByynBNgjfCXfc62yrelCCREWF7oh6wcLd+LOcQmiCKs='


def getDataForToken(token: str):
    return f'grant_type=refresh_token&client_id=39654&refresh_token={urllib.parse.quote(token.encode("utf-8"), safe="")}'


def getToken():
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-API-Key': config.D2TOKEN,
        'Authorization': config.AUTHORIZATION
    }
    data = getDataForToken(requestToken)
    response = requests.post(config.TOKEN_URL, data=data, headers=headers)
    print(response.json())


getToken()
