import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters, CallbackQueryHandler
from db import init_db
from db import add_message
from db import count_messages
from db import list_messages


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

COMMAND_COUNT = 'count'
COMMAND_LIST = 'list'

# добавление клавиатуры


def get_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text='Кол-во сообщений', callback_data=COMMAND_COUNT),
            ],
            [
                InlineKeyboardButton(text='Мои сообщения', callback_data=COMMAND_LIST),
            ],
        ],
    )


def start(update: Update, context: CallbackContext) -> None:
    """Присылает сообщение о том, как работает бот"""
    update.message.reply_text('Привет! Используй /set <секунды>, чтобы установить таймер')


def do_help(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        text="Эхо бот, который сохраняет сообщения в базу с функцией таймера\n\n"
             "Список доступных команд есть в меню\n\n"
             "Так же я отвечую на любое сообщение",
    )


def alarm(context: CallbackContext) -> None:
    """Присылает сообщение"""
    job = context.job
    context.bot.send_message(job.context, text='ВРЕМЯ ИСТЕКЛО!')


def remove_job_if_exists(name: str, context: CallbackContext) -> bool:
    """Удаляет задание, если оно существует"""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


def set_timer(update: Update, context: CallbackContext) -> None:
    """Добавляет таймер"""
    chat_id = update.message.chat_id
    try:
        # args[0] время в секундах
        due = int(context.args[0])
        if due < 0:
            update.message.reply_text('Извени, но мы не можем вернуться в прошлое!')
            return

        job_removed = remove_job_if_exists(str(chat_id), context)
        context.job_queue.run_once(alarm, due, context=chat_id, name=str(chat_id))

        text = 'Таймер успешно установлен!'
        if job_removed:
            text += ' Old one was removed.'
        update.message.reply_text(text)

    except (IndexError, ValueError):
        update.message.reply_text('Используй: /set <секунды>')


def unset(update: Update, context: CallbackContext) -> None:
    """Remove the job if the user changed their mind."""
    chat_id = update.message.chat_id
    job_removed = remove_job_if_exists(str(chat_id), context)
    text = 'Таймер успешно отменен!' if job_removed else 'У вас больше нет активных таймеров.'
    update.message.reply_text(text)


def do_echo(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    text = update.message.text
    reply_text = "Ваш ID = {}\n\n{}".format(chat_id, text)
    update.message.reply_text(
        text=reply_text,
        reply_markup=get_keyboard(),
        )
    # добавление сообщения
    if text:
        add_message(
            user_id=chat_id,
            text=text,
        )


def callback_handler(update: Update, context: CallbackContext):
    user = update.effective_user
    callback_data = update.callback_query.data

    if callback_data == COMMAND_COUNT:
        count = count_messages(user_id=user.id)
        text = f'У вас {count} сообщений!'
    elif callback_data == COMMAND_LIST:
        messages = list_messages(user_id=user.id, limit=5)
        text = '\n\n'.join([f'#{message_id} - {message_text}' for message_id, message_text in messages])
    else:
        text = 'Произош  ла ошибка'

    update.effective_message.reply_text(
        text=text,
    )


def main() -> None:
    """Запускает бота"""
    # Вставляется токен из телеграмма
    updater = Updater("")

    # Подключение базы
    init_db()

    # Диспетчер для добавления команд
    dispatcher = updater.dispatcher

    #  добавление команд
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", do_help))
    dispatcher.add_handler(CommandHandler("set", set_timer))
    dispatcher.add_handler(CommandHandler("unset", unset))
    dispatcher.add_handler(MessageHandler(Filters.text, do_echo))
    dispatcher.add_handler(CallbackQueryHandler(callback_handler))

    # Запуск бота
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
