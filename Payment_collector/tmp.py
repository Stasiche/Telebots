# from ..tokens import payment_collector_token
import sys

sys.path.append("..")
from tokens import payment_collector_token

from datetime import timedelta

from telegram import ReplyKeyboardMarkup
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                          ConversationHandler, PicklePersistence)

import csv
import logging

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

MAIN_PHASE = range(1)

reply_keyboard = [['Get sum']]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
updater = None


def start(update, context):
    reply_text = "Я родилсо"
    update.message.reply_text(reply_text)

    context.user_data['sum'] = 0
    context.user_data['min_payment'] = 0
    context.user_data['max_payment'] = 0
    context.user_data['date_first_payment'] = None

    with open('data.csv', "w", newline='') as csv_file:
        writer = csv.writer(csv_file, delimiter=',')
        writer.writerow(['Дата', 'Сумма'])

    return MAIN_PHASE


def add_payment(update, context):
    with open('data.csv', "a", newline='') as csv_file:
        writer = csv.writer(csv_file, delimiter=',')
        writer.writerow([str(update.message.date + timedelta(hours=3)), str(update.message.text)])

    pay = int(update.message.text)
    context.user_data['sum'] += pay

    if pay < context.user_data['min_payment']:
        context.user_data['min_payment'] = pay
    elif pay > context.user_data['max_payment']:
        context.user_data['max_payment'] = pay

    if context.user_data['date_first_payment'] is None:
        context.user_data['date_first_payment'] = str(update.message.date + timedelta(hours=3))
        context.user_data['min_payment'] = pay
        context.user_data['max_payment'] = pay

    update.message.reply_text('Добавлено, текущая сумма: {}', context.user_data['sum'])

    return MAIN_PHASE


def get_csv(update, context):
    global updater
    with open(r"data.csv", "rb") as file:
        updater.bot.sendDocument(update.message.chat['id'], file)

    return MAIN_PHASE


def get_sum(update, context):
    update.message.reply_text(context.user_data['sum'])
    return MAIN_PHASE


def get_stats(update, context):
    update.message.reply_text('Сумма: {}, Мин/макс: {}/{}, Начало периода: {}: '.format(context.user_data['sum'],
                                                                                        context.user_data['min_payment'],
                                                                                        context.user_data['max_payment'],
                                                                                        context.user_data['date_first_payment'],))
    return MAIN_PHASE


def rage(update, context):
    update.message.reply_text(update.message.from_user['username'] + ', используй цифры!')
    return MAIN_PHASE


def done(update, context):
    update.message.reply_text("Ойойойо")
    return MAIN_PHASE


def main():
    global updater
    # Create the Updater and pass it your bot's token.
    pp = PicklePersistence(filename='pc')
    updater = Updater(payment_collector_token, persistence=pp, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher
    # updater.bot.sendDocument()
    # updater.bot.send_document(telegram.Document('1.txt'))
    # Add conversation handler with the states CHOOSING, TYPING_CHOICE and TYPING_REPLY
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],

        states={
            MAIN_PHASE: [
                CommandHandler(('get_table',), get_csv),
                CommandHandler(('get_sum',), get_sum),
                CommandHandler(('get_stats',), get_stats),
                MessageHandler(Filters.regex('\d+'), add_payment),
                MessageHandler(Filters.regex('\D+'), rage),
            ],
        },

        fallbacks=[MessageHandler(Filters.regex('.+'), done)],
        name="my_conversation",
        persistent=True
    )

    dp.add_handler(conv_handler)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
