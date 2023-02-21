import sys
import logging
import os

import requests
from requests.exceptions import RequestException
import telegram
import time

from dotenv import load_dotenv

import exceptions

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN'),
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN'),
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность переменных окружения."""
    env_var = [
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID
    ]
    for var in env_var:
        if not var:
            logging.critical(
                'Отсутствует обязательная переменная окружения: "{}" '
                'Программа принудительно остановлена.'.format(var)
            )
            sys.exit()


def send_message(bot: telegram.Bot, message: str) -> None:
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except telegram.error.TelegramError as error:
        logging.error(error)
    else:
        logging.debug(f"Бот отправил сообщение: {message}")


def get_api_answer(timestamp: int) -> dict:
    """Делает запрос к эндпоинту API-сервиса."""
    try:
        result = requests.get(ENDPOINT, headers=HEADERS, params=timestamp)
    except RequestException as error:
        raise exceptions.AmbiguousException(error)
    if result.status_code != 200:
        raise exceptions.UnreachableEndpoint(
            f'Эндпоинт {ENDPOINT} недоступен. '
            f'Код ответа API: {result.status_code}'
        )
    return result.json()


def check_response(response: dict) -> None:
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError(
            'Неправильное отображение ответа API'
        )
    if 'homeworks' not in response or 'current_date' not in response:
        raise exceptions.KeyNotFoundException(
            'Отсутствие ожидаемых ключей в ответе API'
        )
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError(
            'Неправильное отображение списка домашних работ'
        )
    return homeworks


def parse_status(homework: list) -> str:
    """Извлекает из ответа API статус конкретной домашней работы."""
    if 'homework_name' not in homework:
        raise KeyError("Такой домашней работы нет")
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        raise ValueError(f"Статуса работы {homework_status} нет")
    verdict = HOMEWORK_VERDICTS[homework_status]
    return (
        f'Изменился статус проверки работы "{homework_name}". {verdict}'
    )


def main():
    """Основная логика работы бота."""
    check_tokens()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if len(homeworks) > 0:
                homework = homeworks[0]
                message = parse_status(homework)
                send_message(bot, message)

            logging.debug('Статус домашней работы не изменился')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(error)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s, %(levelname)s, %(message)s, %(name)s, %(lineno)d',
        handlers=[
            logging.FileHandler("main.log", mode='a'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    main()
