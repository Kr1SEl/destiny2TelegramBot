import requests
import os
import logging
import psycopg2
import json
import sys
import urllib
from dotenv import load_dotenv


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
    return response.json()['refresh_token'], response.json()['access_token']


def getAccessToken():
    load_dotenv()
    result = ''
    try:
        connection = psycopg2.connect(
            host=os.getenv('dbHost'), user=os.getenv('dbUser'), password=os.getenv('dbPassword'), port=os.getenv('dbPort'), dbname=os.getenv('dbName'))
        connection.autocommit = True
        logging.debug('DB connetced succesfully')
        with connection.cursor() as cursor:
            cursor.execute(f"""SELECT * FROM refresh_token
                                            WHERE token_id = 1""")
            logging.debug(
                f'Getting refresh token from DB')
            requestToken = cursor.fetchone()
            result = getToken(requestToken[1])
            logging.debug(
                f'Updating refresh token\nRefresh token is {result[0]}')
            cursor.execute(
                f"""UPDATE refresh_token
                    SET token = \'{result[0]}\' 
                    WHERE token_id = 1;""")
    except Exception as ex:
        logging.error(
            f'Exeption {ex} when trying to connect to DataBase')
        sys.exit()
    finally:
        if connection:
            logging.debug('Closing DB connection')
            connection.close()
    return result[1]
