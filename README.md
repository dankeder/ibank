ibank
=====

Download account statements and transactions from your bank. Currently supported banks:

  - [Fio Banka](http://fio.cz)
  - [Citibank CZ](http://citibank.cz)


How to install
--------------

    python setup.py install


Usage
-----

Each supported bank has its own utility:

  - `ibank-fio`
  - `ibank-citibankcz`

Run them with `--help` to see all available options.

### Citibank CZ

To download transactions from 2013-09-01 to 2013-10-01:

	ibank-citibankcz transactions 2013-09-01 2013-10-01

To download transactions from 2013-09-01 till now:

	ibank-citibankcz transactions 2013-09-01

To download transactions made since the last download:

    ibank-citibankcz transactions

To download the account statement:

	ibank-citibankcz statement 2013 1

To specify the output format use the `--format` option. See `--help` for the
list of available formats.

If you have more than one account use the `--account` to specify which one to
use. Its value should be an integer greater than or equal to 0.

Use the `--output-file` option to change the output file name.

### Fio Banka

To download transactions made from 2013-09-01 to 2013-10-01:

    ibank-fio transactions <token> 2013-09-01 2013-10-01

To download transactions made from 2013-09-01 till now:

    ibank-fio transactions <token> 2013-09-01

To download transactions made since the last download:

    ibank-fio transactions <token>

To download the account statement:

	ibank-citibankcz statement <token> 2013 1

To specify the output format use the `--format` option. See `--help` for the
list of available formats.

Use the `--output-file` option to change the output file name.

See [Fio Banka API](http://www.fio.cz/bank-services/internetbanking-api) on how
to generate the authorization token.


Licence
-------

MIT Licence


Author
------

Dan Keder <dan.keder@gmail.com>
