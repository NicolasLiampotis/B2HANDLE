'''
This module provides the class PIDClientCredentials
which handles the credentials for Handle server
Interaction and for the Search Servlet.

Author: Merret Buurman (DKRZ), 2015-2016

'''

import json
import os
import logging
from b2handle.handleexceptions import CredentialsFormatError
import util
import utilhandle

LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(util.NullHandler())

class PIDClientCredentials(object):
    '''
    Provides authentication information to access a Handle server, either by
    specifying username and password or by providing a json file containing
    the relevant information.

    '''

    @staticmethod
    def load_from_JSON(json_filename):
        '''
        Create a new instance of a PIDClientCredentials with information read
        from a local JSON file.

        :param json_filename: The path to the json credentials file. The json
            file should have the following format:

                .. code:: json

                    {
                        "handle_server_url": "https://url.to.your.handle.server",
                        "username": "index:prefix/suffix",
                        "password": "ZZZZZZZ",
                        "prefix": "prefix_to_use_for_writing_handles",
                        "handleowner": "username_to_own_handles"
                    }

            Any additional key-value-pairs are stored in the instance as
            config.
        :raises: :exc:`~b2handle.handleexceptions.CredentialsFormatError`
        :raises: :exc:`~b2handle.handleexceptions.HandleSyntaxError`
        :return: An instance.
        '''

        jsonfilecontent = json.loads(open(json_filename, 'r').read())
        instance = PIDClientCredentials(**jsonfilecontent)
        return instance


    def __init__(self, **args):
        '''
        Initialize client credentials instance.

        The constructor checks if enough arguments are passed to
        authenticate at a handle server or search servlet. For this,
        the following parameters are checked. Depending on the
        chosen authentication method, only a subset of them are
        required.

        All other parameters passed are stored and can be retrieved
        using 'get_config()'. If a credentials objects is used to
        initialize the client, these key-value pairs are passed on
        to the client constructor.

        :param handle_server_url: Optional. The URL of the Handle System
            server to read from. Defaults to 'https://hdl.handle.net'
        :param username: Optional. This must be a handle value reference in
            the format "index:prefix/suffix". The method will throw an exception
            upon bad syntax or non-existing Handle. The existence or validity
            of the password in the handle is not checked at this moment.
        :param password: Optional. This is the password stored as secret key
            in the actual Handle value the username points to.
        :param handleowner: Optional. The username that will be given admin
            permissions over every newly created handle. By default, it is
            '200:0.NA/xyz' (where xyz is the prefix of the handle being created.
        :param private_key: Optional. The path to a file containing the private
            key that will be used for authentication in write mode. If this is
            specified, a certificate needs to be specified too.
        :param certificate_only: Optional. The path to a file containing the
            client certificate that will be used for authentication in write
            mode. If this is specified, a private key needs to be specified too.
        :param certificate_and_key: Optional. The path to a file containing both
            certificate and private key, used for authentication in write mode.
        :param prefix: Prefix. This is not used by the library, but may be
            retrieved by the user.
        :param \**args: Any other key-value pairs are stored and can be accessed
            using 'get_config()'.
        :raises: :exc:`~b2handle.handleexceptions.HandleSyntaxError`
        '''

        util.log_instantiation(LOGGER, 'PIDClientCredentials', args, ['password','reverselookup_password'])

        # Possible arguments:
        useful_args = [
            'handle_server_url',
            'username',
            'password',
            'private_key',
            'certificate_only',
            'certificate_and_key',
            'prefix',
            'handleowner',
            'reverselookup_password',
            'reverselookup_username',
            'reverselookup_baseuri'
        ]
        util.add_missing_optional_args_with_value_none(args, useful_args)

        # Args that the constructor understands:
        self.__handle_server_url = args['handle_server_url']
        self.__username = args['username']
        self.__password = args['password']
        self.__prefix = args['prefix']
        self.__handleowner = args['handleowner']
        self.__private_key = args['private_key']
        self.__certificate_only = args['certificate_only']
        self.__certificate_and_key = args['certificate_and_key']

        # Other attributes:
        self.__additional_config = None

        # All the other args collected as "additional config":
        self.__additional_config = self.__collect_additional_arguments(args, useful_args)

        # Some checks:
        self.__check_handle_syntax()
        self.__check_file_existence()
        self.__check_if_enough_args_for_revlookup_auth(args)
        self.__check_if_enough_args_for_hs_auth()

    def __collect_additional_arguments(self, args, used_args):
        temp_additional_config = {}
        for argname in args.keys():
            if argname not in used_args:
                temp_additional_config[argname] = args[argname]
        if len(temp_additional_config) > 0:
            return temp_additional_config
        else:
            return None

    def __check_if_enough_args_for_revlookup_auth(self, args):
        cond1 = args['reverselookup_username'] or args['username']
        cond2 = args['reverselookup_password'] or args['password']
        cond3 = args['reverselookup_baseuri']  or args['handle_server_url']
        if cond1 and cond2 and cond3:
            self.__reverselookup = True
            LOGGER.debug('Sufficient information given for reverselookup.')
        else:
            self.__reverselookup = False


    def __check_handle_syntax(self):
        if self.__handleowner:
            utilhandle.check_handle_syntax_with_index(self.__handleowner)
        if self.__username:
            utilhandle.check_handle_syntax_with_index(self.__username)

    def __check_file_existence(self):
        if self.__certificate_only:
            if not os.path.isfile(self.__certificate_only):
                msg = 'The certificate file was not found at the specified path: '+self.__certificate_only
                raise CredentialsFormatError(msg=msg)
        if self.__certificate_and_key:
            if not os.path.isfile(self.__certificate_and_key):
                msg = 'The certificate file was not found at the specified path: '+self.__certificate_and_key
                raise CredentialsFormatError(msg=msg)
        if self.__private_key:
            if not os.path.isfile(self.__private_key):
                msg = 'The private key file was not found at the specified path: '+self.__private_key
                raise CredentialsFormatError(msg=msg)

    def __check_if_enough_args_for_hs_auth(self):

        # Which authentication method?
        authentication_method = None

        # Username and Password
        if self.__username and self.__password:
            authentication_method = 'user_password'

        # Certificate file and Key file
        if self.__certificate_only and self.__private_key:
            authentication_method = 'auth_cert_2files'

        # Certificate and Key in one file
        if self.__certificate_and_key:
            authentication_method = 'auth_cert_1file'

        # None was provided:
        if authentication_method is None:
            if self.__reverselookup is True:
                msg = ('Insufficient credentials for writing to handle '
                       'server, but sufficient credentials for searching.')
                LOGGER.info(msg)
            else:
                msg = ''
                if self.__username and not self.__password:
                    msg += 'Username was provided, but no password. '
                elif self.__password and not self.__username:
                    msg += 'Password was provided, but no username. '
                if self.__certificate_only and not self.__private_key:
                    msg += 'A client certificate was provided, but no private key. '
                elif self.__private_key and not self.__certificate_only:
                    msg += 'A private key was provided, but no client certificate. '
                if self.__reverselookup is None:
                    msg += 'Reverse lookup credentials not checked yet.'
                elif self.__reverselookup is False:
                    msg += 'Insufficient credentials for searching.'
                raise CredentialsFormatError(msg=msg)


    def get_username(self):
        # pylint: disable=missing-docstring
        return self.__username

    def get_password(self):
        # pylint: disable=missing-docstring
        return self.__password

    def get_server_URL(self):
        # pylint: disable=missing-docstring
        return self.__handle_server_url

    def get_prefix(self):
        # pylint: disable=missing-docstring
        return self.__prefix

    def get_handleowner(self):
        # pylint: disable=missing-docstring
        return self.__handleowner

    def get_config(self):
        # pylint: disable=missing-docstring
        return self.__additional_config

    def get_path_to_private_key(self):
        # pylint: disable=missing-docstring
        return self.__private_key

    def get_path_to_file_certificate(self):
        # pylint: disable=missing-docstring
        return self.__certificate_only or self.__certificate_and_key

    def get_path_to_file_certificate_only(self):
        # pylint: disable=missing-docstring
        return self.__certificate_only

    def get_path_to_file_certificate_and_key(self):
        # pylint: disable=missing-docstring
        return self.__certificate_and_key

