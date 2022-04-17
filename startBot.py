import json
import requests
import sys
import os
import data
import pytz
import logging
import psycopg2
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CallbackContext, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, ConversationHandler

# TODO add timezone setter, language select
##################################################### CONFIGURATION #####################################################################################
# logging configuration
logging.basicConfig(level='DEBUG', format='%(levelname)s %(message)s')
logger = logging.getLogger()

# load dotenv
load_dotenv()

# bot configuration
updater = Updater(token=os.getenv('TGTOKEN'))
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


def findBungieUser(update: Update, context: CallbackContext):
    logger.debug('Find Bungie user function entred')
    if update.callback_query is not None:
        update.callback_query.edit_message_reply_markup(None)
    # unicode magic ball
    context.bot.send_message(
        chat_id=update.effective_chat.id, text='\U0001F52E Enter Bungie name:')
    return FINDUSER


def getGlobalStats(update: Update, context: CallbackContext):
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
                if len(jsonSubString) == 1:
                    logger.debug('User succesfully found')
                    context.bot.send_message(
                        chat_id=update.effective_chat.id, text=f"\U00002B50 User <b>{payload['displayName']}#{payload['displayNameCode']}</b> was succesfully found!", parse_mode='HTML')  # unicode success
                    membershipId = jsonSubString[0]['membershipId']
                    membershipType = jsonSubString[0]['membershipType']
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
                    getGlobalStats(update, context)
                    logger.debug(
                        f'Cheching if data is in DB: {update.effective_chat.id}')
                    with connection.cursor() as cursor:
                        cursor.execute(f"""SELECT * FROM users
                                            WHERE chat_id = {update.effective_chat.id}""")
                        if cursor.fetchone() == None:
                            charactersForDB = ' '.join(
                                [str(character) for character in characters])
                            logger.debug(
                                f'Inserting data in DB: {update.effective_chat.id}')
                            cursor.execute(
                                f"""INSERT INTO users (chat_id, membershipId, membershipType, characters) VALUES ({update.effective_chat.id}, \'{membershipId}\', \'{membershipType}\', \'{charactersForDB}\');""")
                    context.bot.send_message(
                        chat_id=update.effective_chat.id, text="\U0001F50E Explore more stats", reply_markup=possibleUserStats())
                else:
                    logging.error(
                        "Enter Type is correct but user not exists")
                    context.bot.send_message(
                        chat_id=update.effective_chat.id, text=f"\U0001F6AB User <b>{splittedName[0]}#{splittedName[1]}</b> does not exist!", parse_mode='HTML', reply_markup=tryAgainKeyboard())  # unicode ERROR
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
    except Exception as ex:
        logger.error(f'Exeption {ex} when trying to connect to DataBase')
        context.bot.send_message(
            chat_id=update.effective_chat.id, text='\U0001F6AB Our database is currently unreachable. Contact @kr1sel to find out whats wrong!')  # unicode ERROR
        sys.exit()
    finally:
        if connection:
            logger.debug('Closing DB connection')
            connection.close()


def whereIsXur(update: Update, context: CallbackContext):
    # todo check location value when xur is not on the place
    pass


def legendaryLostSector(update: Update, context: CallbackContext):
    # todo build db accordingly to ls location
    pass


# TODO
def getRaidStats(update: Update, context: CallbackContext):
    logger.debug('Getting raid stats')
    try:
        connection = psycopg2.connect(
            host=os.getenv('dbHost'), user=os.getenv('dbUser'), password=os.getenv('dbPassword'), port=os.getenv('dbPort'), dbname=os.getenv('dbName'))
        connection.autocommit = True
        logger.debug('DB connetced succesfully')
        with connection.cursor() as cursor:
            cursor.execute(f"""SELECT * FROM users
                           WHERE chat_id = {update.effective_chat.id}""")
            fetchoneReminder = cursor.fetchone()
            membershipId = fetchoneReminder[1]
            membershipType = fetchoneReminder[2]
            url = f'https://www.bungie.net/Platform/Destiny2/{membershipType}/Profile/{membershipId}/?components=Profiles%2CCharacters%2CRecords'
            raidStatRequest = requests.get(
                url, headers=headers).json()['Response']['profileRecords']['data']['records']
            logger.debug(f'Getting raid stats from apt {raidStatRequest}')
            raidResultStr = 'Number of activity closures:\n'
            for raid in data.raids:
                raidStat = raidStatRequest[data.raids[raid]]
                try:
                    progress = raidStat['objectives'][0]['progress']
                except Exception as e:
                    logger.error(
                        f'{e} \nNo progress value for {raid} - {data.raids[raid]}')
                    progress = 0
                finally:
                    raidResultStr += f'{raid}: {progress}\n'
            context.bot.send_message(
                chat_id=update.effective_chat.id, text=raidResultStr)
    except Exception as ex:
        logger.error(
            f'Exeption {ex} when trying to connect to DataBase')
        context.bot.send_message(
            chat_id=update.effective_chat.id, text='\U0001F6AB Our database is currently unreachable. Contact @kr1sel to find out whats wrong!')  # unicode ERROR
        sys.exit()
    finally:
        if connection:
            logger.debug('Closing DB connection')
            connection.close()


# TODO
def getGambitStats(update: Update, context: CallbackContext):
    logger.debug('Getting gambit stats')
    try:
        connection = psycopg2.connect(
            host=os.getenv('dbHost'), user=os.getenv('dbUser'), password=os.getenv('dbPassword'), port=os.getenv('dbPort'), dbname=os.getenv('dbName'))
        connection.autocommit = True
        logger.debug('DB connetced succesfully')
        context.bot.send_message(
            chat_id=update.effective_chat.id, text='There must be Gambit statis in the future!')
    except Exception as ex:
        logger.error(
            f'Exeption {ex} when trying to connect to DataBase')
        context.bot.send_message(
            chat_id=update.effective_chat.id, text='\U0001F6AB Our database is currently unreachable. Contact @kr1sel to find out whats wrong!')  # unicode ERROR
        sys.exit()
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
dispatcher.add_handler(CommandHandler('whereIsXur', whereIsXur))
dispatcher.add_handler(CommandHandler('legendaryLostSector', whereIsXur))
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
