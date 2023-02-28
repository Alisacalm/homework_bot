import json
import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv
from requests.exceptions import RequestException

import exceptions

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

env_var = {
    'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
    'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
    'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
}

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

hw_logger = logging.getLogger(__name__)


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all((PRACTICUM_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN))


def send_message(bot: telegram.Bot, message: str) -> None:
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except telegram.error.TelegramError as error:
        hw_logger.error(
            f'Боту не удалось отправить сообщение: "{message}". {error}'
        )
    else:
        hw_logger.debug(f"Бот отправил сообщение: {message}")


def get_api_answer(timestamp: int) -> dict:
    """Делает запрос к эндпоинту API-сервиса."""
    params = {'from_date': timestamp}
    try:
        result = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except RequestException as error:
        raise exceptions.AmbiguousException(error)
    if result.status_code != HTTPStatus.OK:
        raise exceptions.UnreachableEndpoint(
            f'Эндпоинт {ENDPOINT} недоступен. '
            f'Код ответа API: {result.status_code}'
        )
    try:
        return result.json()
    except json.JSONDecodeError as error:
        raise ValueError(
            f'Возникли трудности при приведении '
            f'ответа API к типам данных Python: {error}'
        )


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
    if not check_tokens():
        hw_logger.critical(
            'Отсутствует обязательная переменная окружения. '
            'Программа принудительно остановлена.'
        )
        sys.exit()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    prev_status = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                homework = homeworks[0]

                if homework['status'] is not prev_status:
                    message = parse_status(homework)
                    send_message(bot, message)
                    prev_status = homework['status']
                hw_logger.debug('Статус домашней работы не изменился')
            hw_logger.debug('Пока нет актуальной домашки')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            hw_logger.error(message)
            prev_error = ''
            if str(error) is not str(prev_error):
                send_message(bot, message)
                prev_error = error
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    hw_logger.setLevel(logging.DEBUG)

    stream_handler = logging.StreamHandler(sys.stdout)
    file_handler = logging.FileHandler("main.log")
    formatter = logging.Formatter(
        '%(asctime)s, %(name)s, %(levelname)s, %(message)s, %(lineno)d'
    )

    hw_logger.addHandler(stream_handler)
    hw_logger.addHandler(file_handler)
    stream_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    main()
