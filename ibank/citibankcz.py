# -*- coding: utf-8 -*-
"""
Download transactions and electronic statements from CitiBank (CZ).

Usage:
  ibank-citibankcz transactions [options] [<from-date> [<to-date>]]
  ibank-citibankcz statement [options] <year> <statement>
  ibank-citibankcz (-h | --help)

Commands:
  transactions                     Get account transactions
  statement                        Get account statement

Options:
  -f <format>, --format <format>   Data format [default: ofx]
  --account <account-id>           Account id if you have multiple accounts [default: 0]
  -o <file>, --output-file <file>  Output file

  <from_date>                      Download transactions since this date. Format:
                                   yyyy-mm-dd. If not specified download transactions
                                   made since the last download.
  <to_date>                        Download transactions till this date. Format:
                                   yyyy-mm-dd. If not specified download transactions
                                   made since <from_date>
  <year>                           Statement year
  <statement>                      Statement number

Transaction formats:
  ofx                              OFX
  csv                              CSV
  xls                              CSV for Microsoft Excel (tab separated values)
  qif-quicken                      QIF for Quicken
  qif-ms                           QIF for Microsoft Money

Statement formats:
  pdf                              PDF document
"""
import os
import sys
import re
import cPickle as pickle
from docopt import docopt
from datetime import date, timedelta
from dateutil.parser import parse as dtparse
from getpass import getpass

import requests


class CitibankCzError(Exception):
    pass


class RequestFailedError(CitibankCzError):
    def __init__(self, msg, response=None):
        super(RequestFailedError, self).__init__(msg)
        self._response = response


class SessionExpiredError(CitibankCzError):
    pass


class LoginFailedError(CitibankCzError):
    pass


class CitibankCz(object):
    def __init__(self):
        # Create a new requests session
        self._session = requests.Session()
        self._session.headers.update({'user-agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:24.0) Gecko/20100101 Firefox/24.0'})

        # List of available statement formats
        self.transaction_formats = [
                'ofx',
                'csv',
                'xls',
                'qif-quicken',
                'qif-ms',
            ]

    def login(self, read_username, read_password, read_sms_password):
        # GET the sign-in dialog and extract the sync token
        url_1 = 'https://production.citibank.cz/CZGCB/JSO/signon/DisplayUsernameSignon.do'
        r = self._session.get(url_1)
        sync_token = self._extract_sync_token(r.text)

        # Send the username/password to the server
        url_2 = 'https://production.citibank.cz/CZGCB/JSO/signon/ProcessUsernameSignon.do'
        payload = {
                'SYNC_TOKEN': sync_token,
                'username': read_username(),
                'password': read_password(),
                'x': 0,
                'y': 0,
                'smsLoginCheck': 'true'
            }
        r = self._session.post(url_2, data=payload)

        if re.search('Litujeme', r.text):
            raise LoginFailedError('Wrong username or password')

        # Extract the sync token
        sync_token = self._extract_sync_token(r.text)

        # Send the SMS password
        url_3 = 'https://production.citibank.cz/CZGCB/JPS/apps/otpstc/StcMain.do'
        payload = {
                'SYNC_TOKEN': sync_token,
                'secureTxnFunction': 'CodeEntry',
                'secureTxnCode': read_sms_password(),
            }

        r = self._session.post(url_3, data=payload)

        if not re.search(r'V.tejte', r.text):
            raise LoginFailedError('Wrong SMS password')

    def logged_in(self):
        ''' Check if the user is logged in.
        '''
        url_1 = 'https://production.citibank.cz/CZGCB/jba/daa/InitializeSubApp.do'
        payload = {
                'TTC': '264',
            }
        r = self._session.post(url_1, data=payload)
        if r.status_code != 200:
            raise RequestFailedError("Initialize subapp request failed", r)

        return (re.search('SignonForm', r.text) is None)

    def get_transactions(self, account_id, from_date, to_date, fmt):
        # Get the format id
        supported_formats = {
                'ofx': 4,
                'csv': 5,
                'xls': 10,
                'qif-quicken': 6,
                'qif-ms': 7,
            }
        fmt_id = supported_formats[fmt]

        # Send request to initialize the app
        url_1 = 'https://production.citibank.cz/CZGCB/jba/daa/InitializeSubApp.do'
        payload = {
                'TTC': '264',
            }
        r = self._session.post(url_1, data=payload)
        if r.status_code != 200:
            raise RequestFailedError("Initialize subapp request failed", r)

        if re.search('SignonForm', r.text):
            raise SessionExpiredError("Session expired")

        # Send request telling them what transactions we want
        url_2 = 'https://production.citibank.cz/CZGCB/jba/daa/startdownloadActivity.do'
        payload = {
                'MISCalendarActivity': 3,
                'cmd': 'process',
                'ruleValueforPreSelect': 'false',
                'ruleValueforAccountSel': 'false',
                'selectAnAcctPhrase': u'Zaškrtněte účty, pro které si chcete uložit přehled pohybů.',
                'warnStatus': 'true',
                'endDateOption': 1,


                'forAccount': 'Selected',       # Selected, All
                'selectedAccountsInForm': account_id,

                'selectedDownloadType': 1,      # 1 - Standardni prehled pohybu na uctu
                                                # 3 - Souhrn s prehledem detailnych pohybu na uctu

                'selectedDownloadFormat': fmt_id,  # 4 - OFX (Active Statement - MS Money)
                                                # 5 - CSV
                                                # 6 - QIF (Quicken, 4 cislice roku)
                                                # 7 - QIF (Microsoft Money, 4 cislice roku)
                                                # 10 - XLS (Excel - hodnoty oddelene tabulatormi)
            }
        if from_date is None:
            payload['saveActivityFor'] = 'Sincelastdownload'
        else:
            payload['saveActivityFor'] = 'DateDownload'
            payload['fromDate'] = from_date.strftime('%d/%m/%Y')
            payload['toDate'] = to_date.strftime('%d/%m/%Y')

        r = self._session.post(url_2, data=payload)
        if r.status_code != 200:
            raise RequestFailedError("Setup request failed", r)

        # Initialize download request
        url_3 = 'https://production.citibank.cz/CZGCB/jba/daa/downloadActivity.do'
        payload = {
                'xyz': ''
            }
        r = self._session.post(url_3, data=payload)
        if r.status_code != 200:
            raise RequestFailedError("Initialize download request failed", r)

        # Download the file finally
        url_4 = 'https://production.citibank.cz/CZGCB/jba/daa/Opendownload.do'
        payload = {
                'xyz': ''
            }
        r = self._session.post(url_4, data=payload)
        if r.status_code != 200:
            raise RequestFailedError("Download request failed", r)

        # Check the content-type
        ctype = r.headers['content-type']
        if fmt == 'ofx' and not ctype.startswith('application/OFX'):
            raise RequestFailedError("Unexpected content-type: {0}".format(ctype), r)
        if fmt == 'csv' and not ctype.startswith('application/csv'):
            raise RequestFailedError("Unexpected content-type: {0}".format(ctype), r)
        if fmt == 'xls' and not ctype.startswith('application/xls'):
            raise RequestFailedError("Unexpected content-type: {0}".format(ctype), r)
        if fmt in ('qif-quicken', 'qif-ms') and not ctype.startswith('application/QIF'):
            raise RequestFailedError("Unexpected content-type: {0}".format(ctype), r)

        return r.text.strip()

    def get_statement(self, account_id, year, statement_id):
        ''' Download the specified PDF account statement.
        '''
        # Send request to initialize the app
        url_1 = 'https://production.citibank.cz/CZGCB/cba/estmtview/InitializeSubApp.do'
        r = self._session.get(url_1)
        if r.status_code != 200:
            raise RequestFailedError("Initialize subapp request failed", r)

        # Select account
        url_2 = 'https://production.citibank.cz/CZGCB/cba/estmtview/FireListqMsg.do'
        payload = {
                'selectedAccountIndex': account_id + 1,
                'pdfSupportedByBrowser': 'false',
                'pdfDisplay': 'Inline',
                'warnStatus': 'true',
            }
        r = self._session.post(url_2, data=payload)
        if r.status_code != 200:
            raise RequestFailedError("Statement download failed", r)

        # Select year
        url_3 = 'https://production.citibank.cz/CZGCB/cba/estmtview/BuildStatementDates.do'
        payload = {
                'selectedAccountIndex': account_id + 1,
                'selectedYear': year,
                'pdfSupportedByBrowser': 'false',
                'pdfDisplay': 'Inline',
                'warnStatus': 'true',
            }
        r = self._session.post(url_3, data=payload)
        if r.status_code != 200:
            raise RequestFailedError("Build statement dates failed", r)

        # Select statement
        url_4 = 'https://production.citibank.cz/CZGCB/cba/estmtview/FireVwstqMsg.do'
        payload = {
                'selectedAccountIndex': account_id + 1,
                'selectedYear': year,
                'statementDateIndex': statement_id,
                'pdfSupportedByBrowser': 'true',
                'pdfDisplay': 'Attachment',
                'warnStatus': 'false',
            }
        r = self._session.post(url_4, data=payload)
        if r.status_code != 200:
            raise RequestFailedError("Build statement #2 failed", r)

        # Download statement
        url_5 = 'https://production.citibank.cz/CZGCB/cba/estmtview/DisplayStatementAction.do'
        payload = {
                'selectedAccountIndex': account_id + 1,
                'selectedYear': year,
                'statementDateIndex': statement_id,
                'pdfSupportedByBrowser': 'true',
                'pdfDisplay': 'Attachment',
                'warnStatus': 'false',
            }
        r = self._session.post(url_5, data=payload)
        if r.status_code != 200:
            raise RequestFailedError("Statement download failed", r)

        # Check content-type
        if r.headers['content-type'] != 'application/pdf':
            raise RequestFailedError("Unexpected content-type: {0}".format(r.headers['content-type']), r)

        return r.content


    def _extract_sync_token(self, string):
        match = re.search(r'name="SYNC_TOKEN" value="(\w+)"', string)
        if match is None:
            raise CitibankCzError('Failed to extract SYNC_TOKEN')
        sync_token = match.group(1)
        return sync_token


def _parse_args():
    opts = docopt(__doc__)

    if opts['transactions']:
        # from-date
        if opts['<from-date>'] is not None:
            from_date = dtparse(opts['<from-date>']).date()
        else:
            from_date = None

        # to-date
        if opts['<to-date>'] is not None:
            to_date = dtparse(opts['<to-date>']).date()
        else:
            to_date = None

        return {
                'cmd': 'transactions',
                'fmt': opts['--format'],
                'account_id': int(opts['--account']),
                'from_date': from_date,
                'to_date': to_date,
                'output_file': opts['--output-file'],
            }

    elif opts['statement']:
        return {
                'cmd': 'statement',
                'year': opts['<year>'],
                'account_id': int(opts['--account']),
                'statement_id': int(opts['<statement>']),
                'output_file': opts['--output-file'],
            }


def read_username():
    sys.stdout.write('Username: ')
    sys.stdout.flush()
    return sys.stdin.readline().strip()


def read_password():
    return getpass('Password: ')


def read_sms_password():
    sys.stdout.write('SMS Password: ')
    sys.stdout.flush()
    return sys.stdin.readline().strip()



def main():
    try:
        # Parse arguments
        args = _parse_args()

        # Try to restore a previous session so we don't have to enter credentials
        # again. Session expires after ~5min (server-side)
        cfgdir = os.path.expanduser('~/.ibank')
        statefile = os.path.join(cfgdir, 'citibankcz.state')
        try:
            bank = pickle.load(open(statefile, 'r'))
        except IOError:
            bank = CitibankCz()
        if not bank.logged_in():
            bank.login(read_username, read_password, read_sms_password)
            if not os.path.isdir(cfgdir):
                os.mkdir(cfgdir)
            pickle.dump(bank, open(statefile, 'w'))

        # Run the command
        if args['cmd'] == 'transactions':
            # Check account ID
            if args['account_id'] < 0:
                raise ValueError("Invalid account_id: {0}".format(args['account_id']))

            # Check format
            if args['fmt'] not in bank.transaction_formats:
                raise ValueError("Invalid format: {0}".format(args['fmt']))

            # If we have from_date, but no to_date, initialize to_date to at most
            # yesterday
            if args['from_date'] is not None and \
                    (args['to_date'] is None or args['to_date'] >= date.today()):
                args['to_date'] = date.today() - timedelta(days=1)

            # Get transactions
            transactions = bank.get_transactions(args['account_id'], args['from_date'],
                    args['to_date'], args['fmt'])

            # Output
            output_file = args['output_file']
            if output_file is None:
                if args['from_date'] is None:
                    output_file = 'citibank_transactions.{0}'.format(args['fmt'])
                else:
                    output_file = 'citibank_transactions_{0}_{1}.{2}'.format(
                            args['from_date'].isoformat(),
                            args['to_date'].isoformat(),
                            args['fmt'])

            with open(output_file, 'w') as fh:
                fh.write(transactions.encode('utf-8'))

            print output_file

        elif args['cmd'] == 'statement':
            # Get statement data
            statement_data = bank.get_statement(args['account_id'], args['year'], args['statement_id'])

            # Output
            output_file = args['output_file']
            if output_file is None:
                output_file = 'citibank_statement_{0}_{1}.pdf'.format(
                        args['year'],
                        args['statement_id'])

            with open(output_file, 'w') as fh:
                fh.write(statement_data)

            print output_file

    except KeyboardInterrupt:
        pass


#  vim: expandtab sw=4
