from http import HTTPStatus
import logging
import os
import time
from typing import Union, Optional
import sys

from dotenv import load_dotenv
import telegram
import requests

from exceptions import (ResponseArgumentTypeError,
                        TimestampArgumentTypeError,
                        InvalidPracticumTokenError, APIUrlResponseError,
                        NoPracticumTokenError, NoTelegamChatIdError,
                        NoTelegramTokenError, UnexpectedHomeworkStatusError,
                        HomeworksFieldTypeError, HomeworkArgumentTypeError)

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger(__name__)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens() -> bool:
    """
    Check the availability of the environment variables
    required for running the bot. If PRACTICUM_TOKEN, TELEGRAM_TOKEN
    or TELEGRAM_CHAT_ID variables are not available,
    raises NoPracticumTokenError, NoTelegramTokenError or
    NoTelegamChatIdError, respectively. Return True otherwise.

    """
    data = {
        (PRACTICUM_TOKEN, 'PRACTICUM_TOKEN', NoPracticumTokenError),
        (TELEGRAM_TOKEN, 'TELEGRAM_TOKEN', NoTelegramTokenError),
        (TELEGRAM_CHAT_ID, 'TELEGRAM_CHAT_ID', NoTelegamChatIdError),
    }
    for env_var, env_var_name, error in data:
        if env_var is None:
            raise error(f'Отсутствует обязательная переменная окружения: '
                        f'{env_var_name}.\n'
                        f'Программа принудительно остановлена.')
    return True


def send_message(bot: telegram.Bot, message: str) -> None:
    """
    Send a Telegram bot message to a telegram user and log it.

    """
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
        logger.debug(f'Бот отправил сообщение: {message}')
    except telegram.error.TelegramError as err:
        logger.error(err)


def get_api_answer(timestamp: Union[int, float]) -> dict:
    """
    Return jsonified api response.

    """
    payload = {'from_date': timestamp}
    try:
        response = requests.get(
            url=ENDPOINT,
            headers=HEADERS,
            params=payload,
            timeout=5,
        )
        res = response.json()
    except requests.RequestException as err:
        raise err(
            f'Ошибка доступа к API {ENDPOINT}'
        )

    if response.status_code in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
        raise InvalidPracticumTokenError(
            'Невалидный токен доступа к Яндекс-Практикум'
        )
    if response.status_code == HTTPStatus.BAD_REQUEST:
        raise TimestampArgumentTypeError(
            f'Некорректный тип параметра {timestamp=} '
            f'функции {get_api_answer.__name__}'
        )
    if response.status_code != HTTPStatus.OK:
        raise APIUrlResponseError(
            f'Произошла ошибка с сервисом {ENDPOINT}.'
        )
    return res


def check_response(response: dict) -> dict:
    """Check the type and fields of API response."""
    if not isinstance(response, dict):
        raise ResponseArgumentTypeError(
            f'Некорректный тип параметра {response=} '
            f'функции {check_response.__name__}'
        )

    homework_key = 'homeworks'
    if homework_key not in response:
        raise KeyError(
            f'Отсутствуют ключ {homework_key} в ответе API'
        )
    result = response[homework_key]
    if not isinstance(result, list):
        raise HomeworksFieldTypeError(
            f'Тип данных поля homeworks ({type(result)}) '
            f'не соответствует ожидаемому (list)'
            f'в функции {check_response.__name__}.'
        )
    return None if not result else result[0]


def parse_status(homework: Optional[dict]) -> str:
    """
    Return string with the homework status.

    """
    if homework is None:
        return 'На ревью нет новых домашек.'
    if not isinstance(homework, dict):
        raise HomeworkArgumentTypeError(
            f'Некорректный тип параметра {homework=} '
            f'функции {parse_status.__name__}'
        )

    status_key = 'status'
    if status_key not in homework:
        raise KeyError(f'Отсутствуют ключ {status_key} в ответе API')

    homework_status = homework[status_key]
    if homework_status not in HOMEWORK_VERDICTS:
        raise UnexpectedHomeworkStatusError(
            'Неожиданный статус домашней работы.'
        )

    homework_name = 'homework_name'
    if homework_name not in homework:
        raise KeyError(f'Отсутствуют ключ {homework_name} в ответе API')

    verdict = HOMEWORK_VERDICTS[homework[status_key]]
    return (f'Изменился статус проверки работы "{homework[homework_name]}". '
            f'{verdict}')


def main():
    """Main logic for runnning the bot."""
    try:
        check_tokens()
    except (NoPracticumTokenError, NoTelegamChatIdError,
            NoTelegramTokenError) as error:
        logger.critical(error)
        return

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    previous_homework_status = None
    previous_error_message = None
    same_error_flag = False

    while True:
        try:
            api_res = get_api_answer(timestamp=timestamp)
            response_res = check_response(api_res)
            message = parse_status(response_res)
            if message == previous_homework_status:
                logger.debug('Статус домашки не поменялся')
                continue
            else:
                previous_homework_status = message

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if message == previous_error_message:
                same_error_flag = True
            else:
                previous_error_message = message

        if not same_error_flag:
            send_message(bot, message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
