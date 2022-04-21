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
        chat_id=update.effective_chat.id, text=f"Hello, Guardian!\nI'm a <b>{context.bot.get_me().first_name}</b> \U0001F30D.\nI was created to help Destiny 2 players check their statistics.\nTo find user send command <i>/findguardian</i>.", parse_mode='HTML')
# unicode Earth


# TODO update with every new command
def helpUser(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=f"\U0001F310 <b>{context.bot.get_me().first_name}</b> was developed to help Destiny 2 players to protect the Last City!\n\nList of commands:\n\n<b>Stat Monitor</b>\n\n/findguardian - find user using BungieID\n\n<b>Useful commands</b>\n\n/whereIsXur - gives current Xûr location and items\n/xurNotifier - turns on notifications about Xûr's arrival\n/stopXurNotifier - stops notifications about Xûr's arrival", parse_mode='HTML')


def findBungieUser(update: Update, context: CallbackContext):
    logger.debug('Find Bungie user function entred')
    if update.callback_query is not None:
        update.callback_query.edit_message_reply_markup(None)
    # unicode magic ball
    context.bot.send_message(
        chat_id=update.effective_chat.id, text='\U0001F52E Enter Bungie name:')
    return FINDUSER


# TODO add checks for users with two-factor
# TODO fix stats
def startWorkWithUser(update: Update, context: CallbackContext):
    logger.debug('Start work with user function entred')
    try:
        connection = psycopg2.connect(
            host=os.getenv('dbHost'), user=os.getenv('dbUser'), password=os.getenv('dbPassword'), port=os.getenv('dbPort'), dbname=os.getenv('dbName'))
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
                membershipId = ''
                membershipType = ''
                if len(jsonSubString) >= 1:
                    for i in range(0, len(jsonSubString)):
                        if(len(jsonSubString[0]['applicableMembershipTypes']) > 0):
                            membershipId = jsonSubString[0]['membershipId']
                            membershipType = jsonSubString[0]['membershipType']
                else:
                    logging.error(
                        "Enter Type is correct but user not exists")
                    context.bot.send_message(
                        chat_id=update.effective_chat.id, text=f"\U0001F6AB User <b>{splittedName[0]}#{splittedName[1]}</b> does not exist!", parse_mode='HTML', reply_markup=tryAgainKeyboard())  # unicode ERROR
                    return
                logger.debug('User succesfully found')
                context.bot.send_message(
                    chat_id=update.effective_chat.id, text=f"\U00002B50 User <b>{payload['displayName']}#{payload['displayNameCode']}</b> was succesfully found!", parse_mode='HTML')  # unicode success
                url = f'https://www.bungie.net/Platform/Destiny2/{membershipType}/Profile/{membershipId}/?components=Profiles%2CCharacters%2CRecords'
                profileRequest = requests.get(
                    url, headers=headers).json()['Response']
                characters = profileRequest['profile']['data']['characterIds']
                charData = ""
                logger.debug('Proceeding through characters')
                for character in characters:
                    classRem = data.classes[f"{profileRequest['characters']['data'][character]['classType']}"]
                    liteRem = profileRequest['characters']['data'][character]['light']
                    # unicode SPARCLE
                    charData += f'{classRem}: {liteRem} \U00002728\n'
                context.bot.send_message(
                    chat_id=update.effective_chat.id, text=f"{charData}", parse_mode='HTML')
                url = f"http://www.bungie.net/Platform/Destiny2/{membershipType}/Account/{membershipId}/Stats/"
                allTimeStats = requests.get(
                    url, headers=headers).json()['Response']['mergedAllCharacters']['results']
                logger.debug('Finding and printing all time stats')
                subStats = allTimeStats['allPvE']['allTime']
                # unicode SHIELD
                strResults = f"<b>PVE Stats</b> \U0001F6E1\n<i>=></i>Matches: <b>{subStats['activitiesEntered']['basic']['displayValue']}</b>\n  Activities: <b>{subStats['activitiesCleared']['basic']['displayValue']}</b>\n  K/D: <b>{subStats['killsDeathsRatio']['basic']['displayValue']}</b>\n"
                subStats = allTimeStats['allPvP']['allTime']
                # unicode TWOSWORDS
                strResults += f"\n<b>PVP Stats</b> \U00002694\n<i>=></i>Matches: <b>{subStats['activitiesEntered']['basic']['displayValue']}</b>\n  Win Ratio: <b>{round((subStats['activitiesWon']['basic']['value']/subStats['activitiesEntered']['basic']['value']) * 100, 2)}</b>\n  K/D: <b>{subStats['killsDeathsRatio']['basic']['displayValue']}</b>\n"
                context.bot.send_message(chat_id=update.effective_chat.id, text=strResults,
                                         parse_mode='HTML')
                logger.debug(
                    f'Cheching if data is in DB: {update.effective_chat.id}')
                with connection.cursor() as cursor:
                    cursor.execute(f"""SELECT * FROM users
                                            WHERE chat_id = \'{update.effective_chat.id}\'""")
                    if cursor.fetchone() == None:
                        charactersForDB = ' '.join(
                            [str(character) for character in characters])
                        logger.debug(
                            f'Inserting data in DB: {update.effective_chat.id}')
                        cursor.execute(
                            f"""INSERT INTO users (chat_id, membershipId, membershipType, characters) VALUES (\'{update.effective_chat.id}\', \'{membershipId}\', \'{membershipType}\', \'{charactersForDB}\');""")
                if update.callback_query != None:
                    update.callback_query.answer()
                context.bot.send_message(
                    chat_id=update.effective_chat.id, text="\U0001F50E Explore more stats", reply_markup=possibleUserStats())
            else:
                logging.error(
                    "Enter Type is incorrect - not 4 numbers in playerCode")
                context.bot.send_message(
                    chat_id=update.effective_chat.id, text='\U0001F6AB Invalid Bungie name!\n(Example: Name#1234)', reply_markup=tryAgainKeyboard())  # unicode ERROR
        else:
            logging.error(
                "Enter Type is incorrect - message has no separator")
            context.bot.send_message(
                chat_id=update.effective_chat.id, text='\U0001F6AB Invalid Bungie name!\n(Example: Name#0123)', reply_markup=tryAgainKeyboard())  # unicode ERROR
    except (psycopg2.OperationalError, psycopg2.errors.LockNotAvailable) as ex:
        logger.error(f'Exeption {ex} when trying to connect to DataBase')
        context.bot.send_message(
            chat_id=update.effective_chat.id, text='\U0001F6AB Our database is currently unreachable. Contact @kr1sel to find out whats wrong!')  # unicode ERROR
        return
    finally:
        if connection:
            logger.debug('Closing DB connection')
            connection.close()


# TODO find out params and locations
# TODO make stickers to send as a xur location
def whereIsXur(update: Update, context: CallbackContext):
    logger.debug('Entering whereIsXur command')
    url = 'https://www.bungie.net/Platform/Destiny2/3/Profile/4611686018505337419/Character/2305843009665375420/Vendors/2190858386/?components=400'
    accessToken = getAccessToken()
    headers = {
        'X-API-KEY': os.getenv('D2TOKEN'),
        'Authorization': f'Bearer {accessToken}',
    }
    logger.debug(f'Acces token received {accessToken}')
    response = requests.request("GET", url, headers=headers).json()
    if response['ErrorCode'] == '1627':
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
    current_jobs = context.job_queue.get_jobs_by_name(name)
    logger.debug(f'Current jobs: {current_jobs}')
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


def notifyAboutXur(context: CallbackContext) -> None:
    job = context.job
    context.bot.send_message(
        job.context, text='\U0001F4C5 Xûr has arrived!\nTo find out his location and item pool write <i>/whereIsXur</i>.', parse_mode='HTML')


# todo make notification 24 hours before xur leaves
# using UTC - (my time - 3h)
def xurNotifier(update: Update, context: CallbackContext):
    logger.debug('Xûr notifier function entred')
    chat_id = update.effective_chat.id
    logger.debug(f'Chat id {chat_id}')
    timeToNotify = datetime.time(
        hour=17, minute=00, second=30, tzinfo=pytz.UTC)
    job.run_daily(callback=notifyAboutXur, days=tuple(
        [4]), time=timeToNotify, context=chat_id, name='xur')
    logger.debug('Job is set')
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text='\U0001F47E <b>Xûr notifier</b> was succesfully set!\nYou are gonna receive a notification every time he appears in the game', parse_mode='HTML')


def stopXurNotifier(update: Update, context: CallbackContext):
    logger.debug('Stop notification function entred')
    job_removed = remove_job_if_exists(
        'xur', context)
    text = ''
    logger.debug(f'Job removed: {job_removed}')
    if job_removed:
        text = "\U00002705 Xûr notifier was stopped. You won't receive notification anymore. To start notifier again write <i>/xurNotifier</i>. Stay safe, Guardian!"
    else:
        text = "\U0001F6AB You have no set notifiers. To start Xûr notifier write <i>/xurNotifier</i>."
    context.bot.send_message(
        chat_id=update.effective_chat.id, text=text, parse_mode='HTML')


def legendaryLostSector(update: Update, context: CallbackContext):
    # todo build db accordingly to ls location
    pass


def getRaidStats(update: Update, context: CallbackContext):
    logger.debug('Getting raid stats')
    try:
        if update.callback_query is not None:
            update.callback_query.edit_message_reply_markup(None)
        connection = psycopg2.connect(
            host=os.getenv('dbHost'), user=os.getenv('dbUser'), password=os.getenv('dbPassword'), port=os.getenv('dbPort'), dbname=os.getenv('dbName'))
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
            raidResultStr = f'<b>Raid Stats</b> \U00002620\n <i>=></i>Raids Completed: <b>{raidStats["activitiesCleared"]["basic"]["displayValue"]}</b>\n  Kills: <b>{raidStats["kills"]["basic"]["displayValue"]}</b>\n  Deaths: <b>{raidStats["deaths"]["basic"]["value"]}</b>\n  K/D: <b>{raidStats["killsDeathsRatio"]["basic"]["displayValue"]}</b>\n  KA/D: <b>{raidStats["killsDeathsAssists"]["basic"]["displayValue"]}</b>\n'
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
            update.callback_query.answer()
            context.bot.send_message(
                chat_id=update.effective_chat.id, text="\U0001F50E Explore more stats", reply_markup=possibleUserStats())
    except Exception as ex:
        logger.error(
            f'Exeption {ex} when trying to connect to DataBase')
        context.bot.send_message(
            chat_id=update.effective_chat.id, text='\U0001F6AB Our database is currently unreachable. Contact @kr1sel to find out whats wrong!')  # unicode ERROR
        return
    finally:
        if connection:
            logger.debug('Closing DB connection')
            connection.close()


def getGambitStats(update: Update, context: CallbackContext):
    logger.debug('Getting gambit stats')
    try:
        if update.callback_query is not None:
            update.callback_query.edit_message_reply_markup(None)
        connection = psycopg2.connect(
            host=os.getenv('dbHost'), user=os.getenv('dbUser'), password=os.getenv('dbPassword'), port=os.getenv('dbPort'), dbname=os.getenv('dbName'))
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
            message = f'<b>Gambit Stats</b> \U0001F98E\n <i>=></i>Matches: <b>{gambitStats["activitiesEntered"]["basic"]["displayValue"]}</b>\n  Wins: <b>{gambitStats["activitiesWon"]["basic"]["displayValue"]}</b>\n  Win Rate: <b>{round((gambitStats["activitiesWon"]["basic"]["value"]/gambitStats["activitiesEntered"]["basic"]["value"]) * 100, 2)}</b>\n  Kills: <b>{gambitStats["kills"]["basic"]["displayValue"]}</b>\n  Deaths: <b>{gambitStats["deaths"]["basic"]["displayValue"]}</b>\n  K/D: <b>{gambitStats["killsDeathsRatio"]["basic"]["displayValue"]}</b>\n  KA/D: <b>{gambitStats["killsDeathsAssists"]["basic"]["displayValue"]}</b>\n  Invasion Kills: <b>{gambitStats["invasionKills"]["basic"]["displayValue"]}</b>'
        context.bot.send_message(
            chat_id=update.effective_chat.id, text=message, parse_mode='HTML')
        update.callback_query.answer()
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="\U0001F50E Explore more stats", reply_markup=possibleUserStats())
    except Exception as ex:
        logger.error(
            f'Exeption {ex} when trying to connect to DataBase')
        context.bot.send_message(
            chat_id=update.effective_chat.id, text='\U0001F6AB Our database is currently unreachable. Contact @kr1sel to find out whats wrong!')  # unicode ERROR
        return
    finally:
        if connection:
            logger.debug('Closing DB connection')
            connection.close()


def unkownReply(update: Update, context: CallbackContext):
    logger.debug('Unknown message received')
    context.bot.send_message(
        chat_id=update.effective_chat.id, text="Unfortunately, I don't know how to answer this request \U0001F61E.\nYou may contact @kr1sel if the bot is broken.")


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


def possibleUserStats():
    keyboard = [[InlineKeyboardButton("Raids \U0001F680", callback_data='raid'),  # unicode ROCKET
                 InlineKeyboardButton("Gambit \U0001F680", callback_data='gambit')],  # unicode ROCKET
                [InlineKeyboardButton("\U0001F52E Find another Guardian", callback_data='anotherUser')]]
    return InlineKeyboardMarkup(keyboard)


##################################################### HANDLERS ###########################################################################################
dispatcher.add_handler(CommandHandler('start', startChat))
dispatcher.add_handler(CommandHandler('help', helpUser))
dispatcher.add_handler(CommandHandler('whereIsXur', whereIsXur))
dispatcher.add_handler(CommandHandler('xurNotifier', xurNotifier))
dispatcher.add_handler(CommandHandler('stopXurNotifier', stopXurNotifier))
dispatcher.add_handler(CommandHandler('lostSector', legendaryLostSector))
dispatcher.add_handler(ConversationHandler(
    entry_points=[CommandHandler('findguardian', findBungieUser)],
    states={
        FINDUSER: [MessageHandler(Filters.text & (
            ~Filters.command), startWorkWithUser)]
    },
    fallbacks=[CommandHandler('findguardian', findBungieUser)],
))
dispatcher.add_handler(MessageHandler(
    Filters.text & ~Filters.command, unkownReply))
dispatcher.add_handler(CallbackQueryHandler(
    findBungieUser, pattern='tryAgain'))
dispatcher.add_handler(CallbackQueryHandler(
    getRaidStats, pattern='raid'))
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
