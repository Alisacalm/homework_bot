import logging
import os

import requests
import telegram
import time

from dotenv import load_dotenv

load_dotenv()

env_var = {
    'PRACTICUM_TOKEN': os.getenv('PRACTICUM_TOKEN'),
    'TELEGRAM_TOKEN': os.getenv('TELEGRAM_TOKEN'),
    'TELEGRAM_CHAT_ID': os.getenv('TELEGRAM_CHAT_ID')

}

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {env_var["PRACTICUM_TOKEN"]}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    for var in env_var:
        if not var:
            logging.critical(
                'Отсутствует обязательная переменная окружения: "{}" '
                'Программа принудительно остановлена.'.format(var)
            )


def send_message(bot, message):
    bot.send_message(
        chat_id=env_var['TELEGRAM_CHAT_ID'],
        text=message,
    )


def get_api_answer(timestamp):
    homeworks = requests.get(ENDPOINT, headers=HEADERS, params=timestamp)
    return homeworks.json()


def check_response(response):
    homeworks = response.get('homeworks')
    if homeworks not in response:
        raise logging.exception('Неожиданный ответ API')

def parse_status(homework):
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    return (
        'Изменился статус проверки работы "{homework_name}": "{verdict}"'
    ).format(
        homework_name=homework_name,
        verdict=HOMEWORK_VERDICTS[homework_status]
    )


def main():
    """Основная логика работы бота."""

    check_tokens()

    bot = telegram.Bot(token=env_var['TELEGRAM_TOKEN'])
    timestamp = int(time.time())

    response = get_api_answer(timestamp)
    homeworks = check_response(response)

    homework = homeworks[0]
    response_2 = get_api_answer(0)

    while True:
        try:
            if response is not response_2:
                message = parse_status(homework)
                send_message(bot, message)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            ...
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
