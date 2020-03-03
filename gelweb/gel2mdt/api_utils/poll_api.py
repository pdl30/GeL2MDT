"""Copyright (c) 2018 Great Ormond Street Hospital for Children NHS Foundation
Trust & Birmingham Women's and Children's NHS Foundation Trust

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import os
import getpass
import requests
import json
import labkey as lk
from ..config import load_config


class PollAPI(object):
    """
    Object entity representing a polling of an API.

    Contains info about the reponse including repsonse code, the json that has
    been returned, the API that has been polled.

    Attributes:
        api (str): which API this particular PollAPI should be polling. Must be
            a key value within server_list.
        endpoint (str): the desired endpoint of the API.
        server_list (dict): a k-v pairing of api names and a tuple which holds:
            [0]: format strings of the api's URL which can be formatted with
            str.format(endpoint='') to give the URL
            [1]: a boolean which indiciates whether the API requires auth. At
            the moment, this is only CIP-API.
        server (f'str): the format string obtained from server_list using api
            as the dict key; server being the 0th index of the associated dict
            value tuple.
        url (str): the URL which should give the desired JSON response. This is
            generated by formatting the 'server' format string with .format(),
            passing in the value for self.endpoint
        headers_required (bool): whether the API requires headers - either
            auth headers or simply Content-Type/Accept headers to specify a
            JSON response instead of XML. Auth headers only required for
            CIP-API at this point. Obtained from server_list using api as the
            dict key; headers_required being the 1 index of the asoociated dict
            value tuple.
        headers (dict): the dict which is passed as a header value when polling
            and API with requests.Session.get(). May be auth headers in the
            case of CIP-API and include a token, or may just specifiy a JSON
            request.
        token_url (str): the URL used to fetch an authentication token. This is
            specific to CIP-API at this point. Generated by class method
            get_auth_headers()
        response_json (dict): the JSON response (as a dict) that returns from
            the polled API.
        response_status (int): the HTTP response code received from the API
            response. Should be 200, but can be validated to check for aberrant
            codes such as 40x and 50x.

    TODO:
        Refactor get_auth_headers() into cip_utils package, since this is
            specific code and does not belong in PollAPI. For now this is fine,
            but will cause issues in case we introduce another API which
            requires authentication.
    """
    def __init__(self, api, endpoint):
        """
        Initialises a PollAPI instance with an api and endpoint.

        api and endpoint values are used to set the correct server variable
        from the server_list, and format an url from the api's server and
        desired endpoint.
        """
        self.config = load_config.LoadConfig().load()
        self.api = api
        self.endpoint = endpoint
        if self.config['use_active_directory'] == "True":
            cip_api_url = "https://cipapi-gms-beta.genomicsengland.nhs.uk/api/2/{endpoint}"
        else:
            cip_api_url = "https://cipapi.genomicsengland.nhs.uk/api/2/{endpoint}"
        self.server_list = {
            "cip_api": (
                cip_api_url,
                True),
            "cip_api_for_report": (
                "https://cipapi.genomicsengland.nhs.uk/api/{endpoint}",
                True),
            "panelapp": (
                "https://panelapp.genomicsengland.co.uk/WebServices/{endpoint}",
                False),
            "ensembl": (
                "https://rest.ensembl.org/{endpoint}",
                True),
            "mutalyzer": (
                "https://mutalyzer.nl/json/{endpoint}",
                False),
            "genenames": (
                "https://rest.genenames.org/{endpoint}",
                True)
        }

        self.server = self.server_list[api][0]
        self.url = self.server.format(endpoint=self.endpoint)
        self.headers_required = self.server_list[api][1]
        self.headers = None

        self.token_url = None
        self.response_json = None  # set upon calling get_json_response()
        self.response_status = None

    def get_json_response(self, content=False):
        """
        Creates a request session which polls the desired API for JSON.

        Request will be tried 20 times (MAX_RETRIES) in the case of failure to
        fetch a proper JSON. This covers connection/retrieval failures, but not
        improper JSON objects which return despite a 200 code. This is instead
        covered by a bool json_poll_sucess. At the end of each response, the
        json library is used to attempt to decode the JSON into a dict. Upon a
        failure, json_poll_sucess remains false and another request Session is
        attempted.
        """
        json_poll_success = False
        while not json_poll_success:
            MAX_RETRIES = 20
            session = requests.Session()
            adapter = requests.adapters.HTTPAdapter(max_retries=MAX_RETRIES)
            session.mount("https://", adapter)

            # IF/ELIF/ELSE tree used to check several conditions. If headers
            # are required (self.headers_required) and they have not yet been
            # set (self.headers = None), then we must set the self.headers
            # value. In the case of CIP-API, we need to fetch auth headers
            # (first if statement), which is handled by the class method
            # get_auth_headers(). If not, then standard headers can be set
            # using get_headers() method instead. If headers are required and
            # they HAVE been set, we can now use a GET method via the request
            # Session to fetch the JSON API response, passing in the
            # server/endpoint and the set headers. Finally, if headers are not
            # required, we can call the GET response immediately without
            # setting headers first.
            if (self.headers_required) and (self.headers is None) and (self.api.startswith('cip_api')):
                # get auth headers if we need them and they're not yet set
                self.get_auth_headers()
                continue
            elif (self.headers_required) and (self.headers is None) and (self.api == 'genenames'):
                self.get_headers()
                continue
            elif (self.headers_required) and (self.headers is None) and (self.api == 'ensembl'):
                self.get_headers()
                continue
            elif (self.headers_required) and (self.headers is not None):
                # auth headers required; have been set
                response = session.get(
                    url=self.url,
                    headers=self.headers)
            elif not self.headers_required:
                # no headers required
                response = session.get(
                    url=self.url)

            if content:
                return response.content  # return the content, which is a JSON
            else:
                # The response may not have a content section, particularly in
                # the case of errors. In this case, the whole response can be
                # treated as a JSON, and will contain error information. We can
                # extract this for debugging purposes - if it is decodable.
                try:
                    self.response_json = response.json()
                    self.response_status = response.status_code
                    json_poll_success = True
                except json.JSONDecodeError as e:
                    continue

                return response.json()

    def get_auth_headers(self):
        """
        Creates a CIP-API token, then creates Accept/Auth header accordingly.

        Token is created based on CIP-API username and password, which should
        be environment variables; class method get_credentials() ensures this.
        Once executed, headers will be set as a class instance attribute.

        Args:
            None

        Returns:
            None
        """
        token_endpoint_list = {
            "cip_api": "get-token/",
            "cip_api_for_report": "get-token/"}
        token_endpoint = token_endpoint_list[self.api]

        self.token_url = self.server.format(endpoint=token_endpoint)
        self.get_credentials()

        if self.config['use_active_directory'] == "True":
            token_response = requests.post(
                url="https://login.microsoftonline.com/{tenant_id}/oauth2/token".format(
                    tenant_id=os.environ["tenant_id"]),
                data="grant_type=client_credentials",
                headers={'Content-Type': "application/x-www-form-urlencoded",},
                auth=(os.environ["client_id"], os.environ["client_secret"])
            )
            token_json = token_response.json()
            token = token_json.get("access_token")
        else:
            token_response = requests.post(
                url=self.token_url,
                json=dict(
                    username=os.environ["cip_api_username"],
                    password=os.environ["cip_api_password"]
                ),
            )
            token_json = token_response.json()
            token = token_json.get("token")
        
        self.headers = {
            "Accept": "application/json",
            "Authorization": "JWT {token}".format(
                token=token)}

    def get_headers(self):
        """
        Creates a HTTP request header which specifically asks for JSON response.

        Once executed, headers will be set as a class instance attribute.

        Args:
            None

        Returns:
            None
        """
        self.headers = {
            'Accept': 'application/json',
        }

    def get_credentials(self):
        """
        Sets AD/CIP-API credentials as environment variables if not already set.

        Will look for AD/CIP-API credentials in the execution shell's environment,
        typically set up in gel2mdt/DAILY_UPDATE.sh for automation. If not set,
        then the execution shell will prompt for a username and hidden password
        to be set as enviroment fields, which will then be destroyed once the
        execution shell terminates. Because this is interacting with the shell
        environment, nothing needs to be returned

        Args:
            None

        Returns:
            None
        """
        if self.config['use_active_directory'] == "True":
            try:
                user = os.environ["tenant_id"]
            except KeyError as e:
                os.environ["tenant_id"] = input("Enter Tenant ID: ")
                os.environ["client_id"] = input("Enter Client ID: ")
                os.environ["client_secret"] = getpass.getpass("Enter Client Secret: ")
        else:
            try:
                user = os.environ["cip_api_username"]
            except KeyError as e:
                os.environ["cip_api_username"] = input("Enter username: ")
                os.environ["cip_api_password"] = getpass.getpass("Enter password: ")