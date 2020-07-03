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
import os
import shutil

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

INIT_PHASE, MAIN_PHASE, SELECT_CAT = range(3)

rm = ReplyKeyboardMarkup([['Delivery', 'Food'], ['Other']], one_time_keyboard=True)
updater = None


def create_new_data_file(path):
    with open(path, "w", newline='') as csv_file:
        writer = csv.writer(csv_file, delimiter=',')
        writer.writerow(['id', 'Пользователь', 'Дата', 'Сумма', 'Тип'])


def send_debts(user_id, debts):
    with open('tmp.csv', "w", newline='') as csv_file:
        writer = csv.writer(csv_file, delimiter=',')
        for el in debts:
            writer.writerow(el)

        send_document(user_id, 'tmp.csv')


def send_document(chat_id, file_path):
    global updater

    with open(file_path, "rb") as csv_file:
        updater.bot.sendDocument(chat_id, csv_file)


class Group:
    def __init__(self, group_name, archive_path=None):
        self.group_name = group_name
        self.members = {}
        self.first_date = None

        create_new_data_file(self.group_name + '_data.csv')

        if archive_path is None:
            self.archive_path = os.path.join('.', os.path.join('Archives', self.group_name))
        else:
            self.archive_path = archive_path

    def reg_member(self, user_id, username):
        self.members[user_id] = {}
        self.members[user_id]['username'] = username
        self.reset_member(user_id)

    def reset_member(self, user_id):
        self.members[user_id]['sum'] = 0
        self.members[user_id]['payments'] = []

    def archive_payments(self):
        if not os.path.exists(self.archive_path):
            os.makedirs(self.archive_path)

        shutil.copy2(self.group_name + '_data.csv', os.path.join(self.archive_path, self.group_name + '_data.csv'))
        create_new_data_file(self.group_name + '_data.csv')

        for user_id in self.members.keys():
            self.reset_member(user_id)

    def get_debts(self):
        n = len(self.members)
        mean = 0
        for el in self.members.values():
            mean += el['sum']
        mean /= n

        debts = []
        for el in self.members.values():
            debts.append((el['sum'] - mean)/n)

        n = len(debts)
        tmp_arr = [[0 for i in range(n)] for j in range(n)]
        for i in range(n):
            for j in range(i, n):
                tmp_arr[i][j] = debts[j] - debts[i]
                tmp_arr[j][i] = -tmp_arr[i][j]
            tmp_arr[i][i] = 0

        members_names = [el['username'] for el in self.members.values()]

        debts_table = [[''] + members_names]
        for i, el in enumerate(members_names):
            debts_table.append([el] + tmp_arr[i])

        return debts_table

    def sync_members(self):
        global updater
        debts = self.get_debts()
        for member_id in self.members.keys():
            if self.members[member_id]['username'] == 'stasiche':
                updater.bot.sendMessage(member_id, 'Енто синхронизация \nВот общая таблица')
                send_debts(member_id, debts)

                updater.bot.sendMessage(member_id, 'Енто синхронизация \nВот общая таблица')



def start(update, context):
    update.message.reply_text("Я родилсо \nВведите имя группы")

    if context.bot_data.get('groups') is None:
        context.bot_data['groups'] = {}
        context.bot_data['user_id_to_group_table'] = {}

    return INIT_PHASE


def user_registration(update, context):
    update.message.reply_text('Выбрана группа: ' + update.message.text)

    group_name = update.message.text
    username = update.message.chat['username']
    user_id = update.message.chat['id']

    if group_name not in context.bot_data['groups'].keys():
        context.bot_data['groups'][group_name] = Group(group_name)

    context.bot_data['groups'][group_name].reg_member(user_id, username)

    context.bot_data['user_id_to_group_table'][user_id] = context.bot_data['groups'][group_name]

    update.message.reply_text('Вводи цену')
    return MAIN_PHASE


def add_payment(update, context):
    user_id = update.message.chat['id']
    group = context.bot_data['user_id_to_group_table'][user_id]

    pay = int(update.message.text)

    context.user_data['tmp_lst'] = [str(user_id), str(group.members[user_id]['username']),
                                    str(update.message.date + timedelta(hours=3)), str(update.message.text)]

    group.members[user_id]['sum'] += pay
    group.members[user_id]['payments'].append((str(update.message.date + timedelta(hours=3)), str(update.message.text)))

    if group.first_date is None:
        group.first_date = str(update.message.date + timedelta(hours=3))

    update.message.reply_text('Выберите категорию', reply_markup=rm)

    return SELECT_CAT


def select_category(update, context):
    user_id = update.message.chat['id']
    group = context.bot_data['user_id_to_group_table'][user_id]

    with open(group.group_name + '_data.csv', "a", newline='') as csv_file:
        writer = csv.writer(csv_file, delimiter=',')
        writer.writerow(context.user_data['tmp_lst'] + [str(update.message.text)])

    update.message.reply_text('Добавлено, текущая сумма: {}\nВводи исчо'.format(group.members[user_id]['sum']))

    return MAIN_PHASE


def get_csv(update, context):
    user_id = update.message.chat['id']
    group = context.bot_data['user_id_to_group_table'][user_id]

    send_document(update.message.chat['id'], group.group_name + '_data.csv')

    return MAIN_PHASE


def get_sum(update, context):
    user_id = update.message.chat['id']
    group = context.bot_data['user_id_to_group_table'][user_id]

    update.message.reply_text(group.members[user_id]['sum'])
    return MAIN_PHASE


def show_debts(update, context):
    user_id = update.message.chat['id']
    group = context.bot_data['user_id_to_group_table'][user_id]

    debts = group.get_debts()
    send_debts(id, debts)

    return MAIN_PHASE


def reset(update, context):
    user_id = update.message.chat['id']
    group = context.bot_data['user_id_to_group_table'][user_id]

    group.reset_member(user_id)
    return MAIN_PHASE


def sync_members(update, context):
    user_id = update.message.chat['id']
    group = context.bot_data['user_id_to_group_table'][user_id]

    group.sync_members()
    return MAIN_PHASE


def rage(update, context):
    update.message.reply_text(update.message.from_user['username'] + ', используй цифры!')
    return MAIN_PHASE


def broke(update, context):
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
            INIT_PHASE: [MessageHandler(Filters.regex('.+'), user_registration)],
            MAIN_PHASE: [
                CommandHandler(('table',), get_csv),
                CommandHandler(('sum',), get_sum),
                CommandHandler(('debts',), show_debts),
                CommandHandler(('reset',), reset),
                CommandHandler(('sync',), sync_members),
                MessageHandler(Filters.regex('\d+'), add_payment),
                MessageHandler(Filters.regex('\D+'), rage),
            ],
            SELECT_CAT: [
                MessageHandler(Filters.regex('^(Delivery|Food|Other)$'), select_category),
            ],
        },

        fallbacks=[MessageHandler(Filters.regex('.+'), broke)],
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
