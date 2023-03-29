from http import HTTPStatus
import logging
import os
import time
from typing import Union, Optional
import sys
import simplejson
import json

from dotenv import load_dotenv
import telegram
import requests

from exceptions import (ResponseArgumentTypeError, NoEnvVarError,
                        TimestampArgumentTypeError,
                        InvalidPracticumTokenError, APIUrlResponseError,
                        UnexpectedHomeworkStatusError,
                        HomeworksFieldTypeError, HomeworkArgumentTypeError,
                        APIResponseJSONDecodeError, APIRequestException)

load_dotenv()

logger = logging.getLogger(__name__)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORKS_KEY = 'homeworks'
STATUS_KEY = 'status'
HOMEWORK_NAME = 'homework_name'
CURRENT_DATE = 'current_date'

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens() -> bool:
    """Check the availability of the environment variables."""
    env_vars = (
        (PRACTICUM_TOKEN, 'PRACTICUM_TOKEN'),
        (TELEGRAM_TOKEN, 'TELEGRAM_TOKEN'),
        (TELEGRAM_CHAT_ID, 'TELEGRAM_CHAT_ID'),
    )
    missing_vars = {var_name: var for var, var_name in env_vars if var is None}

    if missing_vars:
        raise NoEnvVarError(
            f'Отсутствуют обязательные переменные окружения: '
            f'{", ".join(missing_vars.keys())}\n'
            f'Программа принудительно остановлена.'
        )
    return True


def send_message(bot: telegram.Bot, message: str) -> None:
    """Send a Telegram bot message to a telegram user and log it."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
        logger.debug(f'Бот отправил сообщение: {message}')
    except telegram.error.TelegramError as err:
        logger.error(err)


def get_api_answer(timestamp: Union[int, float]) -> dict:
    """Return jsonified API response."""
    func_name = get_api_answer.__name__
    payload = {'from_date': timestamp}
    try:
        response = requests.get(
            url=ENDPOINT,
            headers=HEADERS,
            params=payload,
            timeout=5,
        )
    except requests.RequestException as err:
        raise APIRequestException(
            f'Что-то пошло не так при обращении к {ENDPOINT} '
            f'в функции {func_name}'
        ) from err
    if response.status_code in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
        raise InvalidPracticumTokenError(
            f'Невалидный токен доступа к Яндекс-Практикум '
            f'в функции {func_name}.'
        )
    elif response.status_code == HTTPStatus.BAD_REQUEST:
        raise TimestampArgumentTypeError(
            f'Некорректный тип параметра {timestamp=} '
            f'в функции {func_name}'
        )
    elif response.status_code != HTTPStatus.OK:
        raise APIUrlResponseError(
            f'Произошла ошибка с сервисом {ENDPOINT} '
            f'в функции {func_name}.'
        )
    else:
        try:
            return response.json()
        except (json.JSONDecodeError, simplejson.JSONDecodeError):
            raise APIResponseJSONDecodeError(
                f'Ошибка преобразования ответа API '
                f'в json в функции {func_name}.'
            )


def check_response(response: dict) -> dict:
    """Check the type and fields of API response."""
    func_name = check_response.__name__

    if not isinstance(response, dict):
        raise ResponseArgumentTypeError(
            f'Некорректный тип параметра {response=} '
            f'функции {func_name}'
        )

    if HOMEWORKS_KEY not in response:
        raise KeyError(
            f'Отсутствует ключ {HOMEWORKS_KEY} в ответе API '
            f'в функции {func_name}.'
        )
    if CURRENT_DATE not in response:
        raise KeyError(
            f'Отсутствует ключ {CURRENT_DATE} в ответе API '
            f'в функции {func_name}.'
        )

    homeworks = response[HOMEWORKS_KEY]
    if not isinstance(homeworks, list):
        raise HomeworksFieldTypeError(
            f'Тип данных поля homeworks ({type(homeworks)}) '
            f'не соответствует ожидаемому (list)'
            f'в функции {func_name}.'
        )
    return response


def parse_status(homework: Optional[dict]) -> str:
    """Return string with the homework status."""
    func_name = parse_status.__name__

    if homework is None:
        return 'На ревью нет новых домашек.'
    if not isinstance(homework, dict):
        raise HomeworkArgumentTypeError(
            f'Некорректный тип параметра {homework=} '
            f'функции {func_name}.'
        )

    if STATUS_KEY not in homework:
        raise KeyError(
            f'Отсутствуют ключ {STATUS_KEY} в ответе API '
            f'в функции {func_name}.'
        )

    homework_status = homework[STATUS_KEY]
    if homework_status not in HOMEWORK_VERDICTS:
        raise UnexpectedHomeworkStatusError(
            f'Неожиданный статус домашней работы. '
            f'в функции {func_name}.'
        )

    if HOMEWORK_NAME not in homework:
        raise KeyError(
            f'Отсутствуют ключ {HOMEWORK_NAME} в ответе API'
            f'в функции {func_name}.'
        )

    verdict = HOMEWORK_VERDICTS[homework[STATUS_KEY]]
    return (f'Изменился статус проверки работы "{homework[HOMEWORK_NAME]}". '
            f'{verdict}')


def main():
    """Main logic for runnning the bot."""
    # ловлю, чтобы залогировать
    try:
        check_tokens()
    except NoEnvVarError as err:
        logger.critical(err)
        return

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time()) - RETRY_PERIOD

    previous_error_message = None

    while True:
        try:
            api_response = get_api_answer(timestamp=timestamp)
            checked_response = check_response(api_response)
            homeworks = checked_response[HOMEWORKS_KEY]
            if homeworks:
                message = parse_status(homeworks[0])
                send_message(bot, message)
            else:
                logger.debug('Статус домашек не поменялся')

            timestamp = checked_response[CURRENT_DATE]

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if message != previous_error_message:
                send_message(bot, message)
            else:
                previous_error_message = message

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        filename='main.log',
        format='%(asctime)s [%(levelname)s] %(message)s',
    )
    main()
