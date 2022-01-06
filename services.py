import requests
import asyncio

class BadKeyError(Exception):
    def __init__(self, token):
        super().__init__(f'Invalid API key: {token}')

class NoBalanceError(Exception):
    def __init__(self):
        super().__init__('Insufficient balance')

class NoNumbersError(Exception):
    def __init__(self):
        super().__init__('No phones available')

class CodeNotRecivedError(Exception):
    def __init__(self):
        super().__init__('The code was not received')

class Service(object):
    def __init__(
        self,
        token: str,
        country: str,
        service: str='tg',
        wait_loop_count: int=5
    ):
        self.token = token
        self.country = country
        self.id = None
        self.service = service
        self.wait_loop_count = wait_loop_count

        self.service_api_url = None
    
    def get_balance(self) -> float:
        response = requests.get(f"{self.service_api_url}?api_key={self.token}&action=getBalance")
        return float(response.text.split(':')[-1])
    
    def get_numbers_status(self) -> dict:
        response = requests.get(f"{self.service_api_url}?api_key={self.token}&action=getTopCountriesByService&service={self.service}")
        
        return response.json()
    
    def get_price(self) -> float:
        return 0.5

    async def edit_activation(self, value: int):
        '''
        value:
               -1 = отменить активацию
                1 = Сообщить, что SMS отправлена (необязательно)
                3 = запросить еще один код (бесплатно)
                6 = завершить активацию (если был статус "код получен" - помечает успешно и завершает, если был "подготовка" - удаляет и помечает ошибка, если был статус "ожидает повтора" - переводит активацию в ожидание смс)
                8 = сообщить о том, что номер использован и отменить активацию
        '''
        requests.get(f'{self.service_api_url}?action=setStatus&api_key={self.token}&id={self.id}&status={value}')

    async def wait_while_code_not_exists(self):
        for _ in range(self.wait_loop_count):
            response = requests.get(f'{self.service_api_url}?action=getStatus&api_key={self.token}&id={self.id}')

            if 'STATUS_OK' in response.text:
                return True
            elif 'STATUS_CANCEL' in response.text:
                return

            await asyncio.sleep(60)

    async def get_number(self):
        response = requests.get(f"{self.service_api_url}?action=getNumber&api_key={self.token}&service={self.service}&country={self.country}")
        if 'BAD_KEY' in response.text:
            raise BadKeyError(self.token)

        elif 'NO_BALANCE' in response.text:
            raise NoBalanceError

        elif 'NO_NUMBERS' in response.text:
            raise NoNumbersError

        data = response.text.split(':')
        self.id = data[1]

        return data[2]

    def get_code(self):
        response = requests.get(f'{self.service_api_url}?action=getStatus&api_key={self.token}&id={self.id}')
        return response.text.split(':')[1]

    async def wait_code(self):
        if (await self.wait_while_code_not_exists()):
            return self.get_code()
        else:
            await self.cancel_number()
            raise CodeNotRecivedError

    async def cancel_number(self):
        await self.edit_activation(8)

class SmsActivate(Service):
    def __init__(self, *args):
        super().__init__(*args)
        self.service_api_url = "https://api.sms-activate.org/stubs/handler_api.php"

class SmsHub(Service):
    def __init__(self, *args):
        super().__init__(*args)
        self.service_api_url = "http://smshub.org/stubs/handler_api.php"

class SmsMan(Service):
    def __init__(self, *args):
        super().__init__(*args)
        self.service_api_url = "http://api.sms-man.ru/stubs/handler_api.php"
