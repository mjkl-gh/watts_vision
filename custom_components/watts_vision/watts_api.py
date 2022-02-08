import functools
import logging
import requests

from homeassistant.helpers.typing import (
    HomeAssistantType,
)

_LOGGER = logging.getLogger(__name__)

class WattsApi:
    """Interface to the Watts API."""

    def __init__(self, hass: HomeAssistantType, username: str, password: str):
        """Init dummy hub."""
        self._hass = hass
        self._username = username
        self._password = password
        self._token = None
        self._refresh_token = None
        self._smartHomeData = {}
    
    async def test_authentication(self) -> bool:
        """Test if we can authenticate with the host."""
        try:
            token = await self.getLoginToken()
            return token is not None
        except:
            _LOGGER.exception("Watts Authentication exception")
            return False
    
    async def getLoginToken(self):
        """Get the login token for the Watts Smarthome API"""

        payload = { 
            'grant_type': 'password', 
            'username': self._username,
            'password': self._password, 
            'client_id': 'app-front' 
        }
        func = functools.partial(
            requests.post,
            url = "https://smarthome.wattselectronics.com/auth/realms/watts/protocol/openid-connect/token",
            data = payload
        )
        _LOGGER.debug("Trying to get an access token.")
        request_token_result = await self._hass.async_add_executor_job(func)

        if request_token_result.status_code == 200:
            _LOGGER.debug("Requesting access token succesfull")
            token = request_token_result.json()['access_token']
            self._token = token
            self._refresh_token = request_token_result.json()['refresh_token']
            return token
        else:
            _LOGGER.error("Something went wrong fetching token: {0}".format(request_token_result.status_code))
            raise None

    async def loadData(self):
        """load data from api"""
        smarthomes = await self.loadSmartHomes()
        self._smartHomeData = smarthomes
        
        """load devices for each smart home"""
        if self._smartHomeData is not None:
            for y in range(len(self._smartHomeData)):
                devices = await self.loadDevices(self._smartHomeData[str(y)]['smarthome_id'])
                self._smartHomeData[str(y)]['devices'] = devices

        return True

    async def loadSmartHomes(self, firstTry: bool = True):
        """Load the user data"""
        headers = { 
            'Authorization': 'Bearer {}'.format(self._token) 
        }
        payload = { 
            'token': 'true', 
            'email': self._username, 
            'lang': 'nl_NL' 
        }
        func = functools.partial(
            requests.post,
            url = 'https://smarthome.wattselectronics.com/api/v0.1/human/user/read/',
            headers = headers, 
            data = payload
        )

        user_data_result = await self._hass.async_add_executor_job(func)

        if user_data_result.status_code == 200:
            if user_data_result.json()['code']['code'] == '1' and user_data_result.json()['code']['key'] == 'OK' and user_data_result.json()['code']['value'] == 'OK':
                return user_data_result.json()['data']['smarthomes']
            else:
                if firstTry:
                    # Token may be expired, try to fetch new token
                    token = await self.getLoginToken()
                    return await self.loadSmartHomes(firstTry=False)
                else:
                    _LOGGER.error("Something went wrong fetching user data. Code: {0}, Key: {1}, Value: {2}, Data: {3}".format(user_data_result.json()['code']['code'], user_data_result.json()['code']['key'], user_data_result.json()['code']['value'], user_data_result.json()['data']))
                    return None
        else:
            _LOGGER.error("Something went wrong fetching user data: {0}".format(user_data_result.status_code))
            return None
    
    async def loadDevices(self, smarthome: str, firstTry: bool = True):
        """Load devices for smart home"""

        headers = { 
            'Authorization': 'Bearer {}'.format(self._token) 
        }
        payload = { 
            'token': 'true', 
            'smarthome_id': smarthome, 
            'lang': 'nl_NL' 
        }
        func = functools.partial(
            requests.post,
            url = 'https://smarthome.wattselectronics.com/api/v0.1/human/smarthome/read',
            headers = headers, 
            data = payload
        )

        devices_result = await self._hass.async_add_executor_job(func)

        if devices_result.status_code == 200:
            if devices_result.json()['code']['code'] == '1' and devices_result.json()['code']['key'] == 'OK' and devices_result.json()['code']['value'] == 'OK':
                
                return devices_result.json()['data']['devices']
            else:
                if firstTry:
                    # Token may be expired, try to fetch new token
                    token = await self.getLoginToken()
                    return await self.loadDevices(smarthome, firstTry=False)
                else:
                    _LOGGER.error("Something went wrong fetching user data. Code: {0}, Key: {1}, Value: {2}, Data: {3}".format(devices_result.json()['code']['code'], devices_result.json()['code']['key'], devices_result.json()['code']['value'], devices_result.json()['data']))
                    return None
        else:
            _LOGGER.error("Something went wrong fetching devices: {0}".format(devices_result.status_code))
            return None
    
    async def reloadDevices(self):
        """load devices for each smart home"""
        if self._smartHomeData is not None:
            for y in range(len(self._smartHomeData)):
                devices = await self.loadDevices(self._smartHomeData[str(y)]['smarthome_id'])
                self._smartHomeData[str(y)]['devices'] = devices

        return True
    
    def getSmartHomes(self):
        """Get smarthomes"""
        return self._smartHomeData
    
    async def getDevice(self, smarthome: str, deviceId: str):
        """Get specific device"""
        for y in range(len(self._smartHomeData)):
            if self._smartHomeData[str(y)]['smarthome_id'] == smarthome:
                for x in range(len(self._smartHomeData[str(y)]['devices'])):
                    if self._smartHomeData[str(y)]['devices'][str(x)]['id'] == deviceId:
                        return self._smartHomeData[str(y)]['devices'][str(x)]
        
        return None

    async def pushTemperature(self, smarthome:str, deviceID: str, value: str, gvMode: str, firstTry: bool = True):
        headers = { 
            'Authorization': 'Bearer {}'.format(self._token) 
        }
        payload = {}
        if gvMode == '0':
            payload = {
                'token': 'true', 
                'context': '1', 
                'smarthome_id': smarthome, 
                'query[id_device]': deviceID, 
                'query[time_boost]': '0', 
                'query[consigne_confort]': value, 
                'query[consigne_manuel]': value, 
                'query[gv_mode]': gvMode, 
                'query[nv_mode]': gvMode, 
                'peremption': '15000', 
                'lang': 'nl_NL'
            }
        if gvMode == '1':
            payload = {
                'token': 'true', 
                'context': '1', 
                'smarthome_id': smarthome, 
                'query[id_device]': deviceID, 
                'query[time_boost]': '0', 
                'query[consigne_manuel]': '0', 
                'query[gv_mode]': gvMode, 
                'query[nv_mode]': gvMode, 
                'peremption': '15000', 
                'lang': 'nl_NL'
            }
        if gvMode == '2':
            payload = {
                'token': 'true', 
                'context': '1', 
                'smarthome_id': smarthome, 
                'query[id_device]': deviceID, 
                'query[time_boost]': '0', 
                'query[consigne_hg]': '446', 
                'query[consigne_manuel]': '446', 
                'query[gv_mode]': gvMode, 
                'query[nv_mode]': gvMode, 
                'peremption': '20000', 
                'lang': 'nl_NL'
            }
        if gvMode == '3':
            payload = {
                'token': 'true', 
                'context': '1', 
                'smarthome_id': smarthome, 
                'query[id_device]': deviceID, 
                'query[time_boost]': '0', 
                'query[consigne_eco]': value, 
                'query[consigne_manuel]': value, 
                'query[gv_mode]': gvMode, 
                'query[nv_mode]': gvMode, 
                'peremption': '15000', 
                'lang': 'nl_NL'
            }
        if gvMode == '4':
            payload = {
                'token': 'true', 
                'context': '1', 
                'smarthome_id': smarthome, 
                'query[id_device]': deviceID, 
                'query[time_boost]': '7200', 
                'query[consigne_boost]': value, 
                'query[consigne_manuel]': value, 
                'query[gv_mode]': gvMode, 
                'query[nv_mode]': gvMode, 
                'peremption': '15000', 
                'lang': 'nl_NL'
            }
        if gvMode == '11':
            payload = {
                'token': 'true', 
                'context': '1', 
                'smarthome_id': smarthome, 
                'query[id_device]': deviceID, 
                'query[time_boost]': '0',
                'query[gv_mode]': gvMode, 
                'query[nv_mode]': gvMode, 
                'query[consigne_manuel]': value,
                'peremption': '15000', 
                'lang': 'nl_NL'
            }
        
        func = functools.partial(
            requests.post,
            url = 'https://smarthome.wattselectronics.com/api/v0.1/human/query/push/',
            headers = headers, 
            data = payload
        )

        push_result = await self._hass.async_add_executor_job(func)

        if push_result.status_code == 200:
            if push_result.json()['code']['key'] == 'OK_SET' and push_result.json()['code']['value'] == 'Insert / update success':
                return True
            else:
                if firstTry:
                    # Token may be expired, try to fetch new token
                    token = await self.getLoginToken()
                    return await self.pushTemperature(smarthome, deviceID, value, gvMode, firstTry=False)
                else:
                    _LOGGER.error("Something went wrong updating the device. Code: {0}, Key: {1}, Value: {2}, Data: {3}".format(push_result.json()['code']['code'], push_result.json()['code']['key'], push_result.json()['code']['value'], push_result.json()['data']))
                    return False
        else:
            _LOGGER.error("Something went wrong updating the device: {0}".format(push_result.status_code))
            return False
