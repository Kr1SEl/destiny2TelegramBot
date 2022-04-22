import json
import requests
import sys
import os
import data
import pytz
import logging
import psycopg2
import datetime
from oAuth_v2 import getAccessToken
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CallbackContext, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, ConversationHandler

# TODO language select
# TODO recently searched function
# TODO learn python lambda
# TODO is possible to notify after each commit to reset notifiers?
# TODO implement /weeklyreset - shows time until weekly reset
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
    logger.debug('Strart chat function entred')
    sticker = open('stickers/hello.webp', 'rb')
    context.bot.send_sticker(chat_id=update.effective_chat.id, sticker=sticker)
    context.bot.send_message(
        chat_id=update.effective_chat.id, text=f"""Hello, Guardian!
I'm a <b>{context.bot.get_me().first_name}</b> \U0001F30D.
I was created to help Destiny 2 players check their statistics.
To find user send command /findGuardian.
To find out all possible commands send /help""", parse_mode='HTML')
# unicode Earth


# TODO update with every new command
def helpUser(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=f"""\U0001F310 <b>{context.bot.get_me().first_name}</b> was developed to help Destiny 2 players to protect the Last City!\n
List of commands:\n\n<b>Stat Monitor</b>\n
/findguardian - find user using BungieID
/recentsearch - obtain stats for last searched user\n
<b>Useful commands</b>\n
/weeklyreset - shows time till the weekly reset
/legendarylostsector - shows information about today's Legendary Lost Sector
/whereisxur - gives current Xûr location and items
/xurnotifier - turns on notifications about Xûr's arrival
/stopxurnotifier - stops notifications about Xûr's arrival""", parse_mode='HTML')


def findBungieUser(update: Update, context: CallbackContext):
    logger.debug('Find Bungie user function entred')
    if update.callback_query != None:
        update.callback_query.answer()
    if update.callback_query is not None:
        update.callback_query.edit_message_reply_markup(None)
    # unicode magic ball
    context.bot.send_message(
        chat_id=update.effective_chat.id, text='\U0001F52E Enter Bungie name:')
    return FINDUSER


# TODO fix stats
def getInitialUserStats(context: CallbackContext):
    logger.debug('getInitialUserStats job entred')
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
        # TODO fix stats
        url = f"http://www.bungie.net/Platform/Destiny2/{membershipType}/Account/{membershipId}/Stats/"
        allTimeStats = requests.get(
            url, headers=headers).json()['Response']['mergedAllCharacters']['results']
        logger.debug('Finding and printing all time stats')
        subStats = allTimeStats['allPvE']['allTime']
        # unicode SHIELD
        strResults = f"""<b>PVE Stats</b> \U0001F6E1
    <i>=></i>Matches: <b>{subStats['activitiesEntered']['basic']['displayValue']}</b>
        Activities: <b>{subStats['activitiesCleared']['basic']['displayValue']}</b>
        K/D: <b>{subStats['killsDeathsRatio']['basic']['displayValue']}</b>\n"""
        subStats = allTimeStats['allPvP']['allTime']
        # unicode TWOSWORDS
        strResults += f"""\n<b>PVP Stats</b> \U00002694
    <i>=></i>Matches: <b>{subStats['activitiesEntered']['basic']['displayValue']}</b>
        Win Ratio: <b>{round((subStats['activitiesWon']['basic']['value']/subStats['activitiesEntered']['basic']['value']) * 100, 2)}</b> 
        K/D: <b>{subStats['killsDeathsRatio']['basic']['displayValue']}</b>"""
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
    logger.debug('Start work with user function entred')
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
                context.bot.send_message(
                    chat_id=update.effective_chat.id, text=f"\U0001F6F0 Data is loading, please wait")  # unicode SATELLITE
                jsonSubString = requests.request(
                    "POST", url, headers=headers, data=json.dumps(payload)).json()["Response"]
                if len(jsonSubString) >= 1:
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
                    context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"\U0001F6AB User <b>{splittedName[0]}#{splittedName[1]}</b> does not exist!",
                        parse_mode='HTML', reply_markup=tryAgainKeyboard())  # unicode ERROR
                    return
                logger.debug('User succesfully found')
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"\U00002B50 User <b>{payload['displayName']}#{payload['displayNameCode']}</b> was succesfully found!",
                    parse_mode='HTML')  # unicode success
                if update.callback_query != None:
                    update.callback_query.answer()
                job.run_once(getInitialUserStats, 0,
                             context=update.effective_chat.id)
            else:
                logging.error(
                    "Enter Type is incorrect - not 4 numbers in playerCode")
                context.bot.send_message(
                    chat_id=update.effective_chat.id, text='\U0001F6AB Invalid Bungie name!\n(Example: Name#1234)',
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
            chat_id=update.effective_chat.id,
            text="\U0001F6AB Our database is currently unreachable. Contact @kr1sel to find out what's wrong!")  # unicode ERROR
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
    logger.debug('recentSearch command entred')
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


# TODO find out params and locations
# TODO make stickers to send as a xur location
def whereIsXur(update: Update, context: CallbackContext):
    logger.debug('Entering whereIsXur command')
    context.bot.send_message(
        chat_id=update.effective_chat.id, text=f"\U0001F6F0 Data is loading, please wait")  # unicode SATELLITE
    url = 'https://www.bungie.net/Platform/Destiny2/3/Profile/4611686018505337419/Character/2305843009665375420/Vendors/2190858386/?components=400'
    accessToken = getAccessToken()
    headers = {
        'X-API-KEY': os.getenv('D2TOKEN'),
        'Authorization': f'Bearer {accessToken}',
    }
    logger.debug(f'Acces token received {accessToken}')
    response = requests.request("GET", url, headers=headers).json()
    if response['ErrorCode'] == 1627:
        logger.debug('Xur is not on the place currently')
        context.bot.send_message(
            chat_id=update.effective_chat.id, text='Xûr is not available right now')
    else:
        logger.debug('Xur is avaliable')
        context.bot.send_message(
            chat_id=update.effective_chat.id, text='Xûr is avaliable on Destiny!')
    context.bot.send_message(
        chat_id=update.effective_chat.id, text=response)


def remove_job_if_exists(name: str, context: CallbackContext) -> bool:
    logger.debug('Remove job if exists function entred')
    arrivalJob = context.job_queue.get_jobs_by_name(
        f'xur:{name}')
    leaveJob = context.job_queue.get_jobs_by_name(
        f'xurLeaving:{name}')
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
    context.bot.send_message(
        job.context, text='\U0001F4C5 Xûr has arrived!\nTo find out his location and item pool write /whereIsXur.',
        parse_mode='HTML')


def notifyAboutXurLeaving(context: CallbackContext) -> None:
    logger.debug('Entering notifyAboutXurLeaving job')
    job = context.job
    context.bot.send_message(
        job.context, text="""\U0001F4C5 Xûr is going to leave soon!
Visit him if you haven't already.
To find out his location and item pool write /whereIsXur.""",
        parse_mode='HTML')


# using UTC - (my time - 3h)
def xurNotifier(update: Update, context: CallbackContext):
    current_jobs = context.job_queue.get_jobs_by_name(
        f'xur:{update.effective_chat.id}')
    logger.debug(f'Current jobs: {current_jobs}')
    if current_jobs:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text='\U0001F6AB <b>Xûr Notifier</b> is set already!\nYou will be every time every time he appears in the game. To stop <b>Xûr Notifier</b> write /stopXurNotifier',
                                 parse_mode='HTML')
        return
    logger.debug('Xûr Notifier function entred')
    logger.debug(f'Chat id {update.effective_chat.id}')
    timeToNotify = datetime.time(
        hour=17, minute=00, second=30, tzinfo=pytz.UTC)
    job.run_daily(callback=notifyAboutXur, days=tuple(
        [4]), time=timeToNotify, context=update.effective_chat.id, name=f'xur:{update.effective_chat.id}')
    job.run_daily(callback=notifyAboutXurLeaving, days=tuple(
        [0]), time=timeToNotify, context=update.effective_chat.id, name=f'xurLeaving:{update.effective_chat.id}')
    logger.debug('Job is set')
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text='\U0001F47E <b>Xûr Notifier</b> was succesfully set!\nYou are gonna receive a notification every time he appears in the game. To stop <b>Xûr Notifier</b> write /stopXurNotifier',
                             parse_mode='HTML')


def stopXurNotifier(update: Update, context: CallbackContext):
    logger.debug('Stop notification function entred')
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


def legendaryLostSector(update: Update, context: CallbackContext):
    # todo build db accordingly to ls location
    pass


def getRaidStats(update: Update, context: CallbackContext):
    logger.debug('Getting raid stats')
    context.bot.send_message(
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
            raidResultStr = f"""<b>Raid Stats</b> \U00002620
    <i>=></i>Raids Completed: <b>{raidStats["activitiesCleared"]["basic"]["displayValue"]}</b>
        Kills: <b>{raidStats["kills"]["basic"]["displayValue"]}</b>
        Deaths: <b>{raidStats["deaths"]["basic"]["value"]}</b>
        K/D: <b>{raidStats["killsDeathsRatio"]["basic"]["displayValue"]}</b>
        KA/D: <b>{raidStats["killsDeathsAssists"]["basic"]["displayValue"]}</b>\n"""
            url = f'https://www.bungie.net/Platform/Destiny2/{membershipType}/Profile/{membershipId}/?components=900'
            raidStatRequest = requests.get(
                url, headers=headers).json()['Response']['profileRecords']['data']['records']
            logger.debug(f'Getting raid stats from apt {raidStatRequest}')
            raidResultStr += '<b>Number of activity closures:</b>\n'
            for raid in data.raids:
                raidStat = raidStatRequest[data.raids[raid]]
                try:
                    progress = raidStat['objectives'][0]['progress']
                except Exception as e:
                    logger.error(
                        f'{e} \nNo progress value for {raid} - {data.raids[raid]}')
                    progress = 0
                finally:
                    raidResultStr += f'{raid}: <b>{progress}</b>\n'
            context.bot.send_message(
                chat_id=update.effective_chat.id, text=raidResultStr, parse_mode='HTML')
            context.bot.send_message(
                chat_id=update.effective_chat.id, text="\U0001F50E Explore more stats", reply_markup=possibleUserStats())
    except Exception as ex:
        logger.error(
            f'Exeption {ex} when trying to connect to DataBase')
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='\U0001F6AB Our database is currently unreachable. Contact @kr1sel to find out  wrong!')  # unicode ERROR
        return
    finally:
        if connection:
            logger.debug('Closing DB connection')
            connection.close()


def getGambitStats(update: Update, context: CallbackContext):
    logger.debug('Getting gambit stats')
    context.bot.send_message(
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
            message = f"""<b>Gambit Stats</b> \U0001F98E
    <i>=></i>Matches: <b>{gambitStats["activitiesEntered"]["basic"]["displayValue"]}</b>
        Wins: <b>{gambitStats["activitiesWon"]["basic"]["displayValue"]}</b>
        Win Rate: <b>{round((gambitStats["activitiesWon"]["basic"]["value"]/gambitStats["activitiesEntered"]["basic"]["value"]) * 100, 2)}</b>
        Kills: <b>{gambitStats["kills"]["basic"]["displayValue"]}</b>
        Deaths: <b>{gambitStats["deaths"]["basic"]["displayValue"]}</b>
        K/D: <b>{gambitStats["killsDeathsRatio"]["basic"]["displayValue"]}</b>
        KA/D: <b>{gambitStats["killsDeathsAssists"]["basic"]["displayValue"]}</b>
        Invasion Kills: <b>{gambitStats["invasionKills"]["basic"]["displayValue"]}</b>"""
        context.bot.send_message(
            chat_id=update.effective_chat.id, text=message, parse_mode='HTML')
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="\U0001F50E Explore more stats", reply_markup=possibleUserStats())
    except Exception as ex:
        logger.error(
            f'Exeption {ex} when trying to connect to DataBase')
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='\U0001F6AB Our database is currently unreachable. Contact @kr1sel to find out  wrong!')  # unicode ERROR
        return
    finally:
        if connection:
            logger.debug('Closing DB connection')
            connection.close()


def unkownReply(update: Update, context: CallbackContext):
    logger.debug('Unknown message received')
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Unfortunately, I don't know how to answer this request \U0001F61E.\nYou may contact @kr1sel if the bot is broken.")


# def cancel(context: CallbackContext):
#     user = update.message.from_user
#     logger.debug("User %s canceled the conversation.", user.first_name)
#     update.message.reply_text(
#         'Bye! I hope we can talk again some day.', reply_markup=ReplyKeyboardRemove())
#     if connection:
#         connection.close()


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
dispatcher.add_handler(CommandHandler('recentSearch', recentSearch))
dispatcher.add_handler(CommandHandler('whereIsXur', whereIsXur))
dispatcher.add_handler(CommandHandler('xurNotifier', xurNotifier))
dispatcher.add_handler(CommandHandler('stopXurNotifier', stopXurNotifier))
dispatcher.add_handler(CommandHandler('lostSector', legendaryLostSector))
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
