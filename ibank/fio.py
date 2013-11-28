# -*- coding: utf-8 -*-
"""
Download transactions and electronic statements from Fio Banka (CZ).

Usage:
  ibank-fio transactions [options] <token> [<from-date> [<to-date>]]
  ibank-fio statement [options] <token> <year> <statement>
  ibank-fio (-h | --help)

Commands:
  transactions                     Get account transactions
  statement                        Get account statement

Options:
  --format <format>                Data format [default: ofx]
  --account <account-id>           Account id if you have multiple accounts [default: 0]
  -o <file>, --output-file <file>  Output file

  <token>                          Authorization token
  <from_date>                      Download transactions since this date. Format:
                                   yyyy-mm-dd. If not specified download transactions
                                   made since the last download.
  <to_date>                        Download transactions till this date. Format:
                                   yyyy-mm-dd. If not specified download transactions
                                   made since <from_date>
  <year>                           Statement year
  <statement>                      Statement number

Transaction formats:
  xml, ofx, gpc, csv, html, json, sta

Statement formats:
  xml, ofx, gpc, csv, html, json, sta, pdf
"""
from docopt import docopt

import sys
from docopt import docopt
from dateutil.parser import parse as dtparse
from datetime import date, timedelta

import requests


class FioError(Exception):
    pass


class RequestFailedError(FioError):
    def __init__(self, msg, response=None):
        super(RequestFailedError, self).__init__(msg)
        self._response = response


class Fio(object):
    def __init__(self):
        # Create a new requests session
        self._session = requests.Session()
        self._session.headers.update({'user-agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:24.0) Gecko/20100101 Firefox/24.0'})

        # List of available transaction formats
        self.transaction_formats = [
                'xml',
                'ofx',
                'gpc',
                'csv',
                'html',
                'json',
                'sta',
            ]

        # List of available statement formats
        self.statement_formats = [
                'xml',
                'ofx',
                'gpc',
                'csv',
                'html',
                'json',
                'sta',
                'pdf',
            ]

    def get_transactions(self, token, from_date, to_date, fmt):
        url = 'https://www.fio.cz/ib_api/rest/periods/{token}/{from_date}/{to_date}/transactions.{fmt}'
        url = url.format(
                token=token,
                from_date=from_date.strftime('%Y-%m-%d'),
                to_date=to_date.strftime('%Y-%m-%d'),
                fmt=fmt,
            )
        r = self._session.get(url)
        if r.status_code != 200:
            raise RequestFailedError("Download transactions failed", r)
        return r.text

    def get_last_transactions(self, token, fmt):
        url = 'https://www.fio.cz/ib_api/rest/last/{token}/transactions.{fmt}'
        url = url.format(
                token=token,
                fmt=fmt,
            )
        r = self._session.get(url)
        if r.status_code != 200:
            raise RequestFailedError("Download transactions failed", r)
        return r.text

    def get_statement(self, token, year, statement_id, fmt):
        url = 'https://www.fio.cz/ib_api/rest/by-id/{token}/{year}/{statement_id}/transactions.{fmt}'
        url = url.format(
                token=token,
                year=year,
                statement_id=statement_id,
                fmt=fmt,
            )
        r = self._session.get(url)
        if r.status_code != 200:
            raise RequestFailedError("Download statement failed", r)
        if r.headers['content-type'].startswith('application/pdf'):
            return r.content
        else:
            return r.text


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
                'token': opts['<token>'],
                'from_date': from_date,
                'to_date': to_date,
                'output_file': opts['--output-file'],
            }

    elif opts['statement']:
        return {
                'cmd': 'statement',
                'token': opts['<token>'],
                'year': opts['<year>'],
                'statement_id': int(opts['<statement>']),
                'fmt': opts['--format'],
                'output_file': opts['--output-file'],
            }


def main():
    try:
        # Parse arguments
        args = _parse_args()

        # Create bank object
        bank = Fio()

        # Run the command
        if args['cmd'] == 'transactions':
            # Check the format
            if args['fmt'] not in bank.transaction_formats:
                raise Exception("Invalid format: {0}".format(args['fmt']))

            # If we have from_date, but no to_date, initialize to_date to at most
            # yesterday
            if args['from_date'] is not None and \
                    (args['to_date'] is None or args['to_date'] >= date.today()):
                args['to_date'] = date.today() - timedelta(days=1)

            # Get transactions
            if args['from_date'] is None:
                transactions = bank.get_last_transactions(args['token'], args['fmt'])
            else:
                transactions = bank.get_transactions(args['token'], args['from_date'],
                        args['to_date'], args['fmt'])

            # Output
            output_file = args['output_file']
            if output_file is None:
                if args['from_date'] is None:
                    output_file = 'fio_transactions.{0}'.format(args['fmt'])
                else:
                    output_file = 'fio_transactions_{0}_{1}.{2}'.format(
                            args['from_date'].isoformat(),
                            args['to_date'].isoformat(),
                            args['fmt'])

            with open(output_file, 'w') as fh:
                fh.write(transactions.encode('utf-8'))

            print output_file

        elif args['cmd'] == 'statement':
            statement = bank.get_statement(args['token'], args['year'],
                    args['statement_id'], args['fmt'])

            # Output
            output_file = args['output_file']
            if output_file is None:
                output_file = 'fio_statement_{0}_{1}.{2}'.format(
                        args['year'],
                        args['statement_id'],
                        args['fmt'])
            with open(output_file, 'w') as fh:
                fh.write(statement)
            print output_file

    except KeyboardInterrupt:
        pass


#  vim: expandtab sw=4
