import requests
import json
import datetime
import logging
import urllib.parse
from jose import jwt
from json.decoder import JSONDecodeError


class ConnectApiClient():

    def __init__(self, config):
        self.config = config
        self.jwt = None


    def list_permission(self, externalNetwork):
        url = f'/api/v1/customer/permissions'
        status, result = self.execute_rest_call(externalNetwork, "GET", url)

        return status, result


    def get_advisor_permission(self, externalNetwork, advisorEmail):
        url = f'/api/v1/customer/advisors/advisorEmailAddress/{advisorEmail}/externalNetwork/{externalNetwork}/permissions'
        status, result = self.execute_rest_call(externalNetwork, "GET", url)

        return status, result


    def add_permission(self, externalNetwork, advisorEmail, permissionName):
        url = f'/api/v1/customer/advisors/advisorEmailAddress/{advisorEmail}/externalNetwork/{externalNetwork}/permissions'
        body = {
            "permissionName": permissionName
            }

        status, result = self.execute_rest_call(externalNetwork, "POST", url, json=body)

        return status, result


    def delete_permission(self, externalNetwork, advisorEmail, permissionName):
        url = f'/api/v1/customer/advisors/advisorEmailAddress/{advisorEmail}/externalNetwork/{externalNetwork}/permissions/{permissionName}'
        status, result = self.execute_rest_call(externalNetwork, "DELETE", url)

        return status, result


    def list_entitlements(self, externalNetwork, page_cursor=''):
        base_url = f'/api/v1/customer/entitlements/externalNetwork/{externalNetwork}/advisors'
        next_url = base_url + page_cursor
        status, result = self.execute_rest_call(externalNetwork, "GET", next_url)
        next_cursor = ''
        prev_cursor = ''

        if status == 'OK' and 'pagination' in result:
            if 'next' in result['pagination'] and result['pagination']['next'] is not None:
                next_cursor = result['pagination']['next']
            if 'previous' in result['pagination'] and result['pagination']['previous'] is not None:
                prev_cursor = result['pagination']['previous']

        return status, result, next_cursor, prev_cursor


    def delete_entitlement(self, externalNetwork, symphonyId):
        url = f'/api/v1/customer/entitlements/{symphonyId}/entitlementType/{externalNetwork}'
        status, result = self.execute_rest_call(externalNetwork, "DELETE", url)

        return status, result


    def add_entitlement(self, externalNetwork, symphonyId):
        url = f'/api/v2/customer/entitlements'
        body = {
            "externalNetwork": externalNetwork,
            "symphonyId": symphonyId
            }

        status, result = self.execute_rest_call(externalNetwork, "POST", url, json=body)

        return status, result


    def get_entitlement(self, externalNetwork, symphonyId):
        url = f'/api/v2/customer/advisor/entitlements?externalNetwork={externalNetwork}&advisorSymphonyId={symphonyId}'

        status, result = self.execute_rest_call(externalNetwork, "GET", url)

        return status, result


    def parse_result(self, apiResult, responseCode):
        if apiResult is not None:
            if responseCode not in (200, 201, 204):
                errorMsg = f'ERROR:'
                if 'status' in apiResult:
                    errorMsg = errorMsg + f' - {apiResult["status"]}'
                if 'error' in apiResult:
                    errorMsg = errorMsg + f' - {apiResult["error"]}'
                if 'type' in apiResult:
                    errorMsg = errorMsg + f' - {apiResult["type"]}'
                if 'title' in apiResult:
                    errorMsg = errorMsg + f' - {apiResult["title"]}'
                if 'message' in apiResult:
                    errorMsg = errorMsg + f' - {apiResult["message"]}'
                if 'errorMessage' in apiResult:
                    errorMsg = errorMsg + f' - {apiResult["errorMessage"]}'
                if 'errorCode' in apiResult:
                    errorMsg = errorMsg + f' - {apiResult["errorCode"]}'
                return errorMsg
            else:
                return 'OK'
        else:
            return 'ERROR: No response found from API call'


    def get_session(self, externalNetwork):
        session = requests.Session()

        if self.jwt is not None:
            jwt = self.jwt
        else:
            jwt = self.create_jwt(externalNetwork)

        session.headers.update({
            'Content-Type': "application/json",
            'Authorization': "Bearer " + jwt}
        )

        ## TODO: Implement Proxy support
        # session.proxies.update(self.config.data['proxyRequestObject'])
        if self.config.ssl:
            logging.debug("Setting truststorePath to {}".format(
                self.config.ssl.trust_store_path)
            )
            session.verify = self.config.ssl.trust_store_path

        return session


    def execute_rest_call(self, externalNetwork, method, path, **kwargs):
        results = None
        apiURL = self.config.context.get(externalNetwork).get("apiURL")

        url = apiURL + path
        session = self.get_session(externalNetwork)
        try:
            logging.debug(f'Invoke API URL: {url}')
            response = session.request(method, url, **kwargs)
        except requests.exceptions.ConnectionError as err:
            logging.error(err)
            logging.error(type(err))
            raise

        if response.status_code == 204:
            results = []
        # JWT Expired - Generate new one
        elif response.status_code == 401:
            logging.info("JWT Expired - Reauthenticating...")
            self.jwt = None
            return self.execute_rest_call(externalNetwork, method, path, **kwargs)
        else:
            try:
                results = json.loads(response.text)
            except JSONDecodeError:
                results = response.text

        final_output = self.parse_result(results, response.status_code)
        # logging.debug(results)
        # logging.debug(f'API Output: {final_output}')
        if response.status_code in (200, 201, 204):
            return 'OK', results
        else:
            return 'ERROR', final_output


    def create_jwt(self, externalNetwork):
        with open(self.config.context.get(externalNetwork).get("privateKey").get("path"), 'r') as f:
            content = f.readlines()
            private_key = ''.join(content)
            current_date = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
            expiration_date = current_date + (5*58)

            payload = {
                'sub': 'ces:customer:' + self.config.context.get(externalNetwork).get("publicKeyId"),
                'exp': expiration_date,
                'iat': current_date
            }

            encoded = jwt.encode(payload, private_key, algorithm='RS512')
            f.close()
            self.jwt = encoded
            return encoded
