import json
import requests
import sys
import os
import data
import pytz
import logging
import psycopg2
import datetime
from humanfriendly import format_timespan
from bs4 import BeautifulSoup
from oAuth_v2 import getAccessToken
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CallbackContext, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, ConversationHandler

# TODO implement /lostsector
##################################################### CONFIGURATION #####################################################################################
# logging configuration
logging.basicConfig(level='DEBUG', format='%(levelname)s %(message)s')
logger = logging.getLogger()

# load dotenv
load_dotenv()

# bot configuration
updater = Updater(token=os.getenv('TGTOKEN'), use_context=True)
dispatcher = updater.dispatcher
job = updater.job_queue

# headers configuration
headers = {'X-API-Key': os.getenv('D2TOKEN')}

FINDUSER = range(1)


################################################### BOT #####################################################################################
def startChat(update: Update, context: CallbackContext):
    logger.debug('Entering strartChat command')
    sticker = open('stickers/hello.webp', 'rb')
    context.bot.send_sticker(chat_id=update.effective_chat.id, sticker=sticker)
    context.bot.send_message(
        chat_id=update.effective_chat.id, text=f"""Hello, Guardian!
I'm a <b>{context.bot.get_me().first_name}</b> \U0001F30D.
I was created to help Destiny 2 players check their statistics.
To find user send command /findGuardian.
To find out all possible commands send /help""", parse_mode='HTML')
# unicode Earth


def helpUser(update: Update, context: CallbackContext):
    logger.debug('Entering helpUser command')
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=f"""\U0001F310 <b>{context.bot.get_me().first_name}</b> was developed to help Destiny 2 players to protect the Last City!\n
List of commands:\n\n<b>Stat Monitor</b>\n
/findguardian - find user using BungieID
/recentsearch - obtain stats for last searched user\n
<b>Useful commands</b>\n
/weeklyreset - shows time till the weekly reset
/lostsector - shows information about today's Legendary Lost Sector
/whereisxur - gives current Xûr location and items
/xurnotifier - turns on notifications about Xûr's arrival
/stopxurnotifier - stops notifications about Xûr's arrival""", parse_mode='HTML')


def findBungieUser(update: Update, context: CallbackContext):
    logger.debug('Entering findBungieUser command')
    if update.callback_query != None:
        update.callback_query.answer()
    if update.callback_query is not None:
        update.callback_query.edit_message_reply_markup(None)
    # unicode magic ball
    context.bot.send_message(
        chat_id=update.effective_chat.id, text='\U0001F52E Enter Bungie name:')
    return FINDUSER


def getInitialUserStats(context: CallbackContext):
    logger.debug('Entering getInitialUserStats job')
    try:
        connection = psycopg2.connect(
            host=os.getenv('dbHost'), user=os.getenv('dbUser'),
            password=os.getenv('dbPassword'), port=os.getenv('dbPort'), dbname=os.getenv('dbName'))
        connection.autocommit = True
        logger.debug('DB connetced succesfully')
        job = context.job
        logger.debug(f'Chat id: {job.context}')
        membershipId = ''
        membershipType = ''
        characters = list()
        with connection.cursor() as cursor:
            logger.debug('Setting membershipType and membershipID from DB')
            cursor.execute(f"""SELECT membershipid, membershiptype
                           FROM users
                           WHERE chat_id = \'{job.context}\';""")
            cursorReminder = cursor.fetchone()
            if cursorReminder == None:
                logger.error(
                    f'Record about {job.context} does not exist in database')
                context.bot.send_message(
                    job.context,
                    text=f"""Record about your user was deleted or does not exist \U0001F61E. You may contact @kr1sel if the bot is broken.""",
                    parse_mode='HTML')
                return
            membershipId = cursorReminder[0]
            membershipType = cursorReminder[1]
            logger.debug(
                f'Data obtained from DB for {job.context}: membershipId - {membershipId}, membershipType - {membershipType}')
        url = f'https://www.bungie.net/Platform/Destiny2/{membershipType}/Profile/{membershipId}/?components=Profiles%2CCharacters%2CRecords'
        profileRequest = requests.get(
            url, headers=headers).json()['Response']
        characters = profileRequest['profile']['data']['characterIds']
        with connection.cursor() as cursor:
            logger.debug(f'Setting characters data to database {job.context}')
            charactersForDB = ' '.join(
                [str(character) for character in characters])
            cursor.execute(
                f"""UPDATE users 
                SET characters = \'{charactersForDB}\'
                WHERE chat_id = \'{job.context}\';""")
        charData = ""
        logger.debug('Proceeding through characters')
        for character in characters:
            classRem = data.classes[f"{profileRequest['characters']['data'][character]['classType']}"]
            liteRem = profileRequest['characters']['data'][character]['light']
            # unicode SPARCLE
            charData += f'{classRem}: {liteRem} \U00002728\n'
        context.bot.send_message(
            job.context, text=f"{charData}", parse_mode='HTML')
        url = f"http://www.bungie.net/Platform/Destiny2/{membershipType}/Account/{membershipId}/Stats/"
        allTimeStats = requests.get(
            url, headers=headers).json()['Response']['mergedAllCharacters']['results']
        logger.debug('Finding and printing all time stats')
        subStats = allTimeStats['allPvE']['allTime']
        pveStatsWeighted = round(float(subStats['activitiesCleared']['basic']['displayValue']) * 0.2 
                                 + float(subStats['killsDeathsRatio']['basic']['displayValue']) * 0.8, 3)
        # unicode SHIELD
        strResults = f"""<b>PVE Stats</b> \U0001F6E1
    <i>=></i>Matches: <b>{subStats['activitiesEntered']['basic']['displayValue']}</b>
        Activities: <b>{subStats['activitiesCleared']['basic']['displayValue']}</b>
        K/D: <b>{subStats['killsDeathsRatio']['basic']['displayValue']}</b>
        """
        subStats = allTimeStats['allPvP']['allTime']
        activitiesEntered = int(subStats['activitiesEntered']['basic']['value'])
        activitiesWon = round((int(subStats['activitiesWon']['basic']['value'])/ (activitiesEntered if activitiesEntered > 0 else 1)) * 100, 2);
        pvpStatsWeighted = round((activitiesWon * 0.4
                                + float(subStats['killsDeathsRatio']['basic']['displayValue']) * 100 * 0.6)
                                * (float(subStats['activitiesEntered']['basic']['displayValue'])/100), 3)
        # unicode TWOSWORDS
        strPvpResults = f"""\n\n<b>PVP Stats</b> \U00002694
    <i>=></i>Matches: <b>{activitiesEntered}</b>
        Win Ratio: <b>{activitiesWon}</b> 
        K/D: <b>{subStats['killsDeathsRatio']['basic']['displayValue']}</b>
        """
        pveRank = 100
        pvpRank = 100
        with connection.cursor() as cursor:
            logger.debug(f'Setting weighted stats to database {job.context}')
            cursor.execute(f"""SELECT *
                            FROM stats
                            WHERE membershipid=\'{membershipId}\'""")
            if cursor.fetchone() == None:
                logger.debug(f'Adding user {membershipId} to stats table')
                cursor.execute(f"""INSERT INTO stats (membershipid)
                                VALUES (\'{membershipId}\');""")
            cursor.execute(
                f"""UPDATE stats 
                SET pve_stats={pveStatsWeighted}, pvp_stats={pvpStatsWeighted}
                WHERE membershipid=\'{membershipId}\';""")
            cursor.execute(
                f"""WITH ranked_users AS (
                    SELECT
                        membershipid,
                        pve_stats,
                        PERCENT_RANK() OVER (ORDER BY pve_stats DESC) AS pct_rank
                    FROM
                        stats
                )
                SELECT
                    (pct_rank * 100) AS pct_rank_percentage
                FROM
                    ranked_users
                WHERE
                    membershipid = \'{membershipId}\'; 
                """)
            pveRank = cursor.fetchone()
            
            cursor.execute(
                f"""WITH ranked_users AS (
                    SELECT
                        membershipid,
                        pvp_stats,
                        PERCENT_RANK() OVER (ORDER BY pvp_stats DESC) AS pct_rank
                    FROM
                        stats
                )
                SELECT
                    (pct_rank * 100) AS pct_rank_percentage
                FROM
                    ranked_users
                WHERE
                    membershipid = \'{membershipId}\'; 
                """)
            pvpRank = cursor.fetchone()
        strResults += f"\n🏆 You are in the top <b>{round(float(pveRank[0]), 2)}%</b> of bot users according to the PVE statistics.\n"
        strResults += strPvpResults
        strResults += f"\n🏆 You are in the top <b>{round(float(pvpRank[0]), 2)}%</b> of bot users according to the PVP statistics."
        context.bot.send_message(
            job.context, text=strResults, parse_mode='HTML')
        context.bot.send_message(
            job.context, text="\U0001F50E Explore more stats", reply_markup=possibleUserStats())
    except (psycopg2.OperationalError, psycopg2.errors.InFailedSqlTransaction) as ex:
        logger.error(f'Exeption {ex} when trying to connect to DataBase')
        context.bot.send_message(
            job.context, text="\U0001F6AB Our database is currently unreachable. Contact @kr1sel to find out what's wrong!")  # unicode ERROR
        return
    finally:
        if connection:
            logger.debug('Closing DB connection')
            connection.close()


def startWorkWithUser(update: Update, context: CallbackContext):
    logger.debug('Entering startWorkWithUser command')
    try:
        connection = psycopg2.connect(
            host=os.getenv('dbHost'), user=os.getenv('dbUser'),
            password=os.getenv('dbPassword'), port=os.getenv('dbPort'), dbname=os.getenv('dbName'))
        connection.autocommit = True
        logger.debug('DB connetced succesfully')
        splittedName = update.message.text.split('#')
        if len(splittedName) == 2:
            if len(splittedName[1]) == 4:
                url = "https://www.bungie.net/Platform/Destiny2/SearchDestinyPlayerByBungieName/All"
                payload = {"displayName": splittedName[0],
                           "displayNameCode": splittedName[1]}
                logger.debug(f'User data recieved: {payload}')
                msg = context.bot.send_message(
                    chat_id=update.effective_chat.id, text=f"\U0001F6F0 Data is loading, please wait")  # unicode SATELLITE
                jsonSubString = requests.request(
                    "POST", url, headers=headers, data=json.dumps(payload)).json()
                if int(jsonSubString["ErrorCode"])!=217 and len(jsonSubString["Response"]) >= 1:
                    jsonSubString=jsonSubString["Response"]
                    for i in range(0, len(jsonSubString)):
                        if(len(jsonSubString[0]['applicableMembershipTypes']) > 0):
                            membershipId = jsonSubString[0]['membershipId']
                            membershipType = jsonSubString[0]['membershipType']
                            with connection.cursor() as cursor:
                                logger.debug(
                                    f'Updating Data in db: {update.effective_chat.id}')
                                cursor.execute(f"""SELECT *
                                               FROM users
                                               WHERE chat_id = \'{update.effective_chat.id}\'""")
                                if cursor.fetchone() != None:
                                    logger.debug(
                                        f'User {update.effective_chat.id} exists in DB, deleting')
                                    cursor.execute(f"""DELETE FROM users
                                                    WHERE chat_id = \'{update.effective_chat.id}\';""")
                                cursor.execute(
                                    f"""INSERT INTO users (chat_id, membershipId, membershipType) 
                                    VALUES (\'{update.effective_chat.id}\', \'{membershipId}\', \'{membershipType}\');""")
                else:
                    logging.error(
                        "Enter Type is correct but user not exists")
                    msg.edit_text(f"\U0001F6AB User <b>{splittedName[0]}#{splittedName[1]}</b> does not exist!",
                                  parse_mode='HTML', reply_markup=tryAgainKeyboard())  # unicode ERROR
                    return
                logger.debug('User succesfully found')
                msg.edit_text(f"\U00002B50 User <b>{payload['displayName']}#{payload['displayNameCode']}</b> was succesfully found!",
                              parse_mode='HTML')  # unicode success
                if update.callback_query != None:
                    update.callback_query.answer()
                job.run_once(getInitialUserStats, 0,
                             context=update.effective_chat.id)
            else:
                logging.error(
                    "Enter Type is incorrect - not 4 numbers in playerCode")
                msg.edit_text('\U0001F6AB Invalid Bungie name!\n(Example: Name#1234)',
                              reply_markup=tryAgainKeyboard())  # unicode ERROR
        else:
            logging.error(
                "Enter Type is incorrect - message has no separator")
            context.bot.send_message(
                chat_id=update.effective_chat.id, text='\U0001F6AB Invalid Bungie name!\n(Example: Name#0123)',
                reply_markup=tryAgainKeyboard())  # unicode ERROR
    except (psycopg2.OperationalError, psycopg2.errors.InFailedSqlTransaction) as ex:
        logger.error(f'Exeption {ex} when trying to connect to DataBase')
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="\U0001F6AB Our database is currently unreachable. Contact @kr1sel to find out what's wrong!")
        return
    finally:
        if connection:
            logger.debug('Closing DB connection')
            connection.close()


def proceedWithUser(update: Update, context: CallbackContext):
    if update.callback_query != None:
        update.callback_query.answer()
    if update.callback_query is not None:
        update.callback_query.edit_message_reply_markup(None)
    context.bot.send_message(
        chat_id=update.effective_chat.id, text=f"\U0001F6F0 Data is loading, please wait")  # unicode SATELLITE
    job.run_once(getInitialUserStats, 0,
                 context=update.effective_chat.id)


def recentSearch(update: Update, context: CallbackContext):
    logger.debug('Entering recentSearch command')
    try:
        if update.callback_query != None:
            update.callback_query.answer()
        if update.callback_query is not None:
            update.callback_query.edit_message_reply_markup(None)
        connection = psycopg2.connect(
            host=os.getenv('dbHost'), user=os.getenv('dbUser'),
            password=os.getenv('dbPassword'), port=os.getenv('dbPort'), dbname=os.getenv('dbName'))
        connection.autocommit = True
        logger.debug('DB connetced succesfully')
        with connection.cursor() as cursor:
            cursor.execute(f"""SELECT membershipid, membershiptype
                           FROM users
                           WHERE chat_id = \'{update.effective_chat.id}\'""")
            cursorReminder = cursor.fetchone()
            if cursorReminder == None:
                context.bot.send_message(
                    chat_id=update.effective_chat.id, text="\U0001F6AB Looks like you did not use /finduser command before!")
            else:
                membershipId = cursorReminder[0]
                membershipType = cursorReminder[1]
                url = f'https://www.bungie.net/Platform/Destiny2/{membershipType}/Profile/{membershipId}/?components=100'
                userData = requests.get(
                    url, headers=headers).json()['Response']['profile']['data']['userInfo']
                context.bot.send_message(
                    chat_id=update.effective_chat.id, text=f"\U00002B50 Last searched user <b>{userData['bungieGlobalDisplayName']}#{userData['bungieGlobalDisplayNameCode']}</b>.\nWould you like to proceed?", parse_mode='HTML', reply_markup=recentSearchReply())
    except (psycopg2.OperationalError, psycopg2.errors.InFailedSqlTransaction) as ex:
        logger.error(f'Exeption {ex} when trying to connect to DataBase')
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="\U0001F6AB Our database is currently unreachable. Contact @kr1sel to find out what's wrong!")  # unicode ERROR
        return
    finally:
        if connection:
            logger.debug('Closing DB connection')
            connection.close()


def parseXurInventory(xurResponse, chatID, context: CallbackContext) -> bool:
    logger.debug('Entering parseXurInventory job')
    context.bot.send_message(
        chat_id=chatID, text='Xûr brought such exotic items:')
    saleItems = xurResponse['Response']['sales']['data']
    exoticItems = list()
    for key in saleItems.keys():
        if len(saleItems[key]['costs']) == 1:
            exoticItems.append(
                (saleItems[key]['itemHash'], saleItems[key]['costs'][0]['quantity']))
    exoticItems.pop(0)
    for item in exoticItems:
        response = requests.get(
            f'https://www.bungie.net/Platform/Destiny2/Manifest/DestinyInventoryItemDefinition/{item[0]}', headers=headers).json()["Response"]
        messageAddition = ''
        if response["classType"] == 3:
            messageAddition = f'\U0001F52B {response["itemTypeAndTierDisplayName"]}'
        else:
            messageAddition = f'{data.classes[str(response["classType"])]} {response["itemTypeAndTierDisplayName"]}'
        context.bot.send_message(
            chat_id=chatID, text=f'{messageAddition}\n<b>{response["displayProperties"]["name"]}</b> - Price: <b>{item[1]}</b> LS \U0001F48E', parse_mode='HTML')
        # imgLink = response["displayProperties"]["icon"]
        imgLink = response["screenshot"]
        context.bot.send_photo(
            chatID, f'https://www.bungie.net{imgLink}')
    return True


def whereIsXur(update: Update, context: CallbackContext):
    logger.debug('Entering whereIsXur command')
    msg = context.bot.send_message(
        chat_id=update.effective_chat.id, text=f"\U0001F6F0 Data is loading, please wait")  # unicode SATELLITE
    today = datetime.datetime.now(tz=pytz.UTC)
    logger.debug(f'Current time: {today}')
    url = 'https://www.bungie.net/Platform/Destiny2/3/Profile/4611686018505337419/Character/2305843009665375420/Vendors/2190858386/?components=400,402'
    accessToken = getAccessToken()
    headers = {
        'X-API-KEY': os.getenv('D2TOKEN'),
        'Authorization': f'Bearer {accessToken}',
    }
    logger.debug(f'Acces token received {accessToken}')
    response = requests.request("GET", url, headers=headers).json()
    if response['ErrorCode'] == 1627:
        logger.debug('Xur is NOT avaliable right now')
        nextDate = today + datetime.timedelta(days=(4-today.weekday()) % 7, hours=(17-today.hour),
                                              minutes=(0-today.minute), seconds=(0-today.second))
        logger.debug(f'Time when Xur appears next time: {nextDate}')
        dateStr = str(nextDate.ctime())
        msg.edit_text(f"""\U0001F5FF Xûr is not available right now. 
He will arrive in:
    <b>{format_timespan((nextDate-today).total_seconds())}</b>
<i>=></i>
    <b>{dateStr[:len(dateStr)-4]}, UTC</b> \U000023F1
Set /xurnotifier so you don't miss his visit \U0001F47E""", parse_mode='HTML')
    else:
        logger.debug('Xur is avaliable')
        location = response['Response']['vendor']['data']['vendorLocationIndex']
        nextDate = today + datetime.timedelta(days=(1-today.weekday()) % 7, hours=(17-today.hour),
                                              minutes=(0-today.minute), seconds=(0-today.second))
        logger.debug(f'Time when Xur appears next time: {nextDate}')
        dateStr = str(nextDate.ctime())
        msg.edit_text(f"""\U0001F389 Xûr is avaliable on Destiny!
You may find him in <b>{data.locations[location]}</b>
He will leave with the weekly reset in:
    <b>{format_timespan((nextDate-today).total_seconds())}</b>
<i>=></i>
    <b>{dateStr[:len(dateStr)-4]}, UTC</b> \U000023F1""", parse_mode='HTML')
        sticker = open(f'stickers/location{location}.webp', 'rb')
        context.bot.send_sticker(
            chat_id=update.effective_chat.id, sticker=sticker)
        logger.debug('Parsing Xur inventory')
        inventoryParsed = parseXurInventory(
            response, update.effective_chat.id, context)
        logger.debug(f'Inventory parsed: {inventoryParsed}')


def remove_job_if_exists(name: str, context: CallbackContext) -> bool:
    logger.debug('Entering remove_job_if_exists function ')
    arrivalJob = context.job_queue.get_jobs_by_name(
        f'xurAppears:{name}')
    leaveJob = context.job_queue.get_jobs_by_name(
        f'xurLeaves:{name}')
    logger.debug(f'Current jobs: {arrivalJob} and {leaveJob}')
    if not arrivalJob:
        return False
    for job in arrivalJob:
        job.schedule_removal()
    for job in leaveJob:
        job.schedule_removal()
    return True


def notifyAboutXur(context: CallbackContext) -> None:
    logger.debug('Entering notifyAboutXur job')
    job = context.job
    logger.debug(job.context)
    context.bot.send_message(
        job.context, text='\U0001F4C5 Xûr has arrived!\nTo find out his location and item pool write /whereIsXur.',
        parse_mode='HTML')


def notifyAboutXurLeaving(context: CallbackContext) -> None:
    logger.debug('Entering notifyAboutXurLeaving job')
    job = context.job
    context.bot.send_message(
        job.context, text="""\U0001F4C5 Xûr is going to leave soon!
Visit him if you haven't already. \U000023F1
To find out his location and item pool write /whereIsXur.""",
        parse_mode='HTML')


# using UTC - (my time - 3h)
def xurNotifier(update: Update, context: CallbackContext):
    logger.debug('Entering xurNotifier function')
    current_jobs = context.job_queue.get_jobs_by_name(
        f'xurAppears:{update.effective_chat.id}')
    logger.debug(f'Current jobs: {current_jobs}')
    if current_jobs:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text='\U0001F6AB <b>Xûr Notifier</b> is set already!\nYou will be every time every time he appears in the game. To stop <b>Xûr Notifier</b> write /stopXurNotifier',
                                 parse_mode='HTML')
        return
    logger.debug(f'Chat id {update.effective_chat.id}')
    logger.debug('Calculate when xur appears')
    today = datetime.datetime.now(tz=pytz.UTC)
    nextDate = today + datetime.timedelta(days=(4-today.weekday()) % 7, hours=(17-today.hour),
                                          minutes=(0-today.minute), seconds=(0-today.second))
    timeInSecondsXurAppears = (nextDate-today).total_seconds()
    logger.debug(f'Time till next xur appearent: {timeInSecondsXurAppears}')
    job.run_repeating(callback=notifyAboutXur, first=timeInSecondsXurAppears, interval=604800,
                      context=update.effective_chat.id, name=f'xurAppears:{update.effective_chat.id}')
    logger.debug('Calculate when xur leaves')
    nextDate = today + datetime.timedelta(days=(1-today.weekday()) % 7, hours=(17-today.hour),
                                          minutes=(0-today.minute), seconds=(0-today.second))
    timeInSecondsXurLeaves = (nextDate-today).total_seconds()
    logger.debug(f'Time till second xur notifier: {timeInSecondsXurLeaves}')
    job.run_repeating(callback=notifyAboutXurLeaving, first=timeInSecondsXurLeaves, interval=604800,
                      context=update.effective_chat.id, name=f'xurLeaves:{update.effective_chat.id}')
    logger.debug('Job is set')
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text='\U0001F47E <b>Xûr Notifier</b> was succesfully set!\nYou are gonna receive a notification every time he appears in the game. To stop <b>Xûr Notifier</b> write /stopXurNotifier',
                             parse_mode='HTML')


def stopXurNotifier(update: Update, context: CallbackContext):
    logger.debug('Entering stopNotification command')
    job_removed = remove_job_if_exists(
        f'{update.effective_chat.id}', context)
    text = ''
    logger.debug(f'Job removed: {job_removed}')
    if job_removed:
        text = "\U00002705 Xûr Notifier was stopped. You won't receive notification anymore. To start notifier again write /xurNotifier. Stay safe, Guardian!"
    else:
        text = "\U0001F6AB You have no set notifiers. To start Xûr notifier write /xurNotifier."
    context.bot.send_message(
        chat_id=update.effective_chat.id, text=text, parse_mode='HTML')


def weeklyReset(update: Update, context: CallbackContext):
    logger.debug('Entering weekly reset command')
    today = datetime.datetime.now(tz=pytz.UTC)
    logger.debug(f'Current time: {today}')
    nextDate = today + datetime.timedelta(days=(1-today.weekday()) % 7, hours=(17-today.hour),
                                          minutes=(0-today.minute), seconds=(0-today.second))
    logger.debug(f'Time of the next reset: {nextDate}')
    dateStr = str(nextDate.ctime())
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"""\U0001F4A0 The next weekly reset will be held in 
    <b>{format_timespan((nextDate-today).total_seconds())}</b>
<i>=></i>
    <b>{dateStr[:len(dateStr)-4]}, UTC</b> \U000023F1""",
        parse_mode='HTML')


def legendaryLostSector(update: Update, context: CallbackContext):
    logger.debug('Entering lostSector command')
    msg = context.bot.send_message(
        chat_id=update.effective_chat.id, text=f"\U0001F6F0 Data is loading, please wait")
    # context.bot.send_message(chat_id=update.effective_chat.id,
    #                          text='\U0001FA90 Feature is currently in development. Please, be patient!')
    url = 'https://www.todayindestiny.com'
    content = BeautifulSoup(requests.get(url).text, 'lxml')
    allEventCards = content.find_all('div', class_='eventCardHeaderText')
    lostSector = ''
    lootType = 'None'
    for eventCard in allEventCards:
        if eventCard.find('p', class_='eventCardHeaderSet').text.strip() == 'Lost Sector':
            logger.debug('Lost Sector Data Found')
            lostSector = eventCard.find('p', class_='eventCardHeaderName').text
            # TODO obtain item data
            break
    if lostSector == '':
        msg.edit_text(
            "\U0001F6AB Unable to parse data about Lost Sector. Contact @kr1sel to find out  wrong!")
    elif lostSector == 'Unknown':
        msg.edit_text(
            "\U0001FA90 Lost Sector is currently unknown. Seems you're playing close to the begining of a new season and the rotation is still being figured out.")
    else:
        msg.edit_text(
            f'\U0001FA90 Lost Sector is {lostSector}. You may receive {lootType} for completing it solo.\n Data is parsed form https://www.todayindestiny.com')


def getRaidStats(update: Update, context: CallbackContext):
    logger.debug('Entering getRaidStats command')
    msg = context.bot.send_message(
        chat_id=update.effective_chat.id, text=f"\U0001F6F0 Data is loading, please wait")  # unicode SATELLITE
    try:
        if update.callback_query != None:
            update.callback_query.answer()
        if update.callback_query is not None:
            update.callback_query.edit_message_reply_markup(None)
        connection = psycopg2.connect(
            host=os.getenv('dbHost'), user=os.getenv('dbUser'),
            password=os.getenv('dbPassword'), port=os.getenv('dbPort'), dbname=os.getenv('dbName'))
        connection.autocommit = True
        logger.debug('DB connetced succesfully')
        with connection.cursor() as cursor:
            cursor.execute(f"""SELECT * FROM users
                           WHERE chat_id = \'{update.effective_chat.id}\'""")
            fetchoneReminder = cursor.fetchone()
            membershipId = fetchoneReminder[1]
            membershipType = fetchoneReminder[2]
            url = f'https://www.bungie.net/Platform/Destiny2/{membershipType}/Account/{membershipId}/Character/0/Stats/'
            raidStats = requests.get(
                url, headers=headers).json()['Response']['raid']['allTime']
            raidsCleared = int(raidStats["activitiesCleared"]["basic"]["displayValue"]);
            raidStatsWeighted = (float(raidStats["killsDeathsAssists"]["basic"]["displayValue"]) * 100) * (raidsCleared/100)
            raidResultStr = f"""<b>Raid Stats</b> \U00002620
    <i>=></i>Raids Completed: <b>{raidsCleared}</b>
        Kills: <b>{raidStats["kills"]["basic"]["displayValue"]}</b>
        Deaths: <b>{raidStats["deaths"]["basic"]["value"]}</b>
        K/D: <b>{raidStats["killsDeathsRatio"]["basic"]["displayValue"]}</b>
        KA/D: <b>{raidStats["killsDeathsAssists"]["basic"]["displayValue"]}</b>\n"""
            url = f'https://www.bungie.net/Platform/Destiny2/{membershipType}/Profile/{membershipId}/?components=900'
            raidStatRequest = requests.get(
                url, headers=headers).json()['Response']['profileRecords']['data']['records']
            logger.debug(f'Getting raid stats from apt {raidStatRequest}')
            raidResultStr += '<b>Number of activity closures:</b>\n\n'
            for raid in data.raids:
                raidStat = raidStatRequest[data.raids[raid]]
                try:
                    progress = raidStat['objectives'][0]['progress']
                except Exception as e:
                    logger.error(
                        f'{e} \nNo progress value for {raid} - {data.raids[raid]}')
                    progress = 0
                finally:
                    raidResultStr += f'{raid}: <b>{progress}</b>\n\n'
            raidRank = 100
            with connection.cursor() as cursor:
                logger.debug(f'Updating weighted stats for raids to database')
                cursor.execute(
                    f"""UPDATE stats
                    SET raid_stats={raidStatsWeighted}
                    WHERE membershipid=\'{membershipId}\';""")
                
                cursor.execute(
                f"""WITH ranked_users AS (
                    SELECT
                        membershipid,
                        raid_stats,
                        PERCENT_RANK() OVER (ORDER BY raid_stats DESC) AS pct_rank
                    FROM
                        stats
                )
                SELECT
                    (pct_rank * 100) AS pct_rank_percentage
                FROM
                    ranked_users
                WHERE
                    membershipid = \'{membershipId}\'; 
                """)
                raidRank = cursor.fetchone()
            raidResultStr += f"\n🏆 You are in the top <b>{round(float(raidRank[0]), 2)}%</b> of bot users according to the Raid statistics."
            msg.edit_text(raidResultStr, parse_mode='HTML')
            context.bot.send_message(
                chat_id=update.effective_chat.id, text="\U0001F50E Explore more stats", reply_markup=possibleUserStats())
    except Exception as ex:
        logger.error(
            f'Exeption {ex} when trying to connect to DataBase')
        msg.edit_text(
            '\U0001F6AB Our database is currently unreachable. Contact @kr1sel to find out  wrong!')
        return
    finally:
        if connection:
            logger.debug('Closing DB connection')
            connection.close()


def getGambitStats(update: Update, context: CallbackContext):
    logger.debug('Entering getGambitStats command')
    msg = context.bot.send_message(
        chat_id=update.effective_chat.id, text=f"\U0001F6F0 Data is loading, please wait")  # unicode SATELLITE
    try:
        if update.callback_query != None:
            update.callback_query.answer()
        if update.callback_query is not None:
            update.callback_query.edit_message_reply_markup(None)
        connection = psycopg2.connect(
            host=os.getenv('dbHost'), user=os.getenv('dbUser'),
            password=os.getenv('dbPassword'), port=os.getenv('dbPort'), dbname=os.getenv('dbName'))
        connection.autocommit = True
        logger.debug('DB connetced succesfully')
        with connection.cursor() as cursor:
            cursor.execute(f"""SELECT * FROM users
                           WHERE chat_id = \'{update.effective_chat.id}\'""")
            fetchoneReminder = cursor.fetchone()
            membershipId = fetchoneReminder[1]
            membershipType = fetchoneReminder[2]
            url = f'https://www.bungie.net/Platform/Destiny2/{membershipType}/Account/{membershipId}/Character/0/Stats/'
            gambitStats = requests.get(
                url, headers=headers).json()['Response']['allPvECompetitive']['allTime']
            activitiesEntered = int(gambitStats["activitiesEntered"]["basic"]["displayValue"])
            winRatio = round(float(gambitStats["activitiesWon"]["basic"]["value"]) / (activitiesEntered if activitiesEntered > 0 else 1) * 100, 2)
            gambitStatsWeighted = (winRatio * 0.2 
                                   + float(gambitStats["killsDeathsAssists"]["basic"]["displayValue"]) * 10 * 0.4 
                                   + (float(gambitStats["invasionKills"]["basic"]["displayValue"]) / (activitiesEntered if activitiesEntered > 0 else 1)) * 100 * 0.3 
                                   + activitiesEntered * 0.1)
            gambitStatsWeighted = round(gambitStatsWeighted, 3)
            message = f"""<b>Gambit Stats</b> \U0001F98E
    <i>=></i>Matches: <b>{activitiesEntered}</b>
        Wins: <b>{gambitStats["activitiesWon"]["basic"]["displayValue"]}</b>
        Win Rate: <b>{winRatio}</b>
        Kills: <b>{gambitStats["kills"]["basic"]["displayValue"]}</b>
        Deaths: <b>{gambitStats["deaths"]["basic"]["displayValue"]}</b>
        K/D: <b>{gambitStats["killsDeathsRatio"]["basic"]["displayValue"]}</b>
        KA/D: <b>{gambitStats["killsDeathsAssists"]["basic"]["displayValue"]}</b>
        Invasion Kills: <b>{gambitStats["invasionKills"]["basic"]["displayValue"]}</b>
        """
        gambitRank = 100
        with connection.cursor() as cursor:
            logger.debug(f'Updating weighted stats for gambit to database')
            cursor.execute(
                f"""UPDATE stats
                SET gambit_stats={gambitStatsWeighted}
                WHERE membershipid=\'{membershipId}\';""")
            cursor.execute(
                f"""WITH ranked_users AS (
                    SELECT
                        membershipid,
                        gambit_stats,
                        PERCENT_RANK() OVER (ORDER BY gambit_stats DESC) AS pct_rank
                    FROM
                        stats
                )
                SELECT
                    (pct_rank * 100) AS pct_rank_percentage
                FROM
                    ranked_users
                WHERE
                    membershipid = \'{membershipId}\'; 
                """)
            gambitRank = cursor.fetchone()
            message += f"\n🏆 You are in the top <b>{round(float(gambitRank[0]), 2)}%</b> of bot users according to the Gambit statistics."
        msg.edit_text(message, parse_mode='HTML')
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="\U0001F50E Explore more stats", reply_markup=possibleUserStats())
    except Exception as ex:
        logger.error(
            f'Exeption {ex} when trying to connect to DataBase')
        msg.edit_text(
            '\U0001F6AB Our database is currently unreachable. Contact @kr1sel to find out  wrong!')
        return
    finally:
        if connection:
            logger.debug('Closing DB connection')
            connection.close()


def unkownReply(update: Update, context: CallbackContext):
    logger.debug('Entering unknownReply command')
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Unfortunately, I don't know how to answer this request \U0001F61E.\nYou may contact @kr1sel if the bot is broken.")



###################################################### KEYBOARDS #####################################################################################
def tryAgainKeyboard():
    keyboard = [[InlineKeyboardButton(
        "Try again! \U0001F680", callback_data='tryAgain')]]  # unicode rocket
    return InlineKeyboardMarkup(keyboard)


def recentSearchReply():
    keyboard = [[InlineKeyboardButton("Show Stats \U0001F680", callback_data='proceedWithUser')],  # unicode ROCKET
                [InlineKeyboardButton("\U0001F52E Find another Guardian", callback_data='anotherUser')]]
    return InlineKeyboardMarkup(keyboard)


def possibleUserStats():
    keyboard = [[InlineKeyboardButton("Raids \U0001F680", callback_data='raid'),  # unicode ROCKET
                 InlineKeyboardButton("Gambit \U0001F680", callback_data='gambit')],  # unicode ROCKET
                [InlineKeyboardButton("\U0001F52E Find another Guardian", callback_data='anotherUser')]]
    return InlineKeyboardMarkup(keyboard)


##################################################### HANDLERS ###########################################################################################
dispatcher.add_handler(CommandHandler('start', startChat))
dispatcher.add_handler(CommandHandler('help', helpUser))
dispatcher.add_handler(CommandHandler('recentsearch', recentSearch))
dispatcher.add_handler(CommandHandler('whereisxur', whereIsXur))
dispatcher.add_handler(CommandHandler('xurnotifier', xurNotifier))
dispatcher.add_handler(CommandHandler('stopxurnotifier', stopXurNotifier))
dispatcher.add_handler(CommandHandler('lostsector', legendaryLostSector))
dispatcher.add_handler(CommandHandler('weeklyreset', weeklyReset))
dispatcher.add_handler(ConversationHandler(
    entry_points=[CommandHandler('findGuardian', findBungieUser)],
    states={
        FINDUSER: [MessageHandler(Filters.text & (
            ~Filters.command), startWorkWithUser)]
    },
    fallbacks=[CommandHandler('findGuardian', findBungieUser)],
))
dispatcher.add_handler(MessageHandler(
    Filters.text & Filters.command, unkownReply))
dispatcher.add_handler(CallbackQueryHandler(
    findBungieUser, pattern='tryAgain'))
dispatcher.add_handler(CallbackQueryHandler(
    getRaidStats, pattern='raid'))
dispatcher.add_handler(CallbackQueryHandler(
    proceedWithUser, pattern='proceedWithUser'))
dispatcher.add_handler(CallbackQueryHandler(
    getGambitStats, pattern='gambit'))
dispatcher.add_handler(CallbackQueryHandler(
    findBungieUser, pattern='anotherUser'))


##################################################### MAIN ###########################################################################################
def main():
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
