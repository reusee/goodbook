#!/usr/bin/env python2
# coding: utf8

import sys
import re
import time
from decimal import *
import collections

from transaction import *

Entry = collections.namedtuple('Entry', ['account', 'currency', 'amount', 'line_number'])

class ParseError(Exception): pass

def read_file(file_name):
  return open(file_name, 'r').read()

def split_transactions(ledger):
  ledger = ledger.splitlines()
  transactions = []
  line_number = 0
  for line in ledger:
    line_number += 1
    indent = len(line) - len(line.lstrip())
    line = line.strip()
    if not line: continue
    if indent == 0: # new transaction
      transactions.append([(line_number, line)])
    else: # entry
      try:
        transactions[-1].append((line_number, line))
      except IndexError:
        raise ParseError("line %d: invalid entry indentation" % line_number)
  return transactions

def _parse_transaction(transaction_lines):
  transaction = Transaction()

  line_number, line = transaction_lines[0]
  date_digits = re.search('([0-9]+).*?([0-9]+).*?([0-9]+)', line)
  if not date_digits:
    raise ParseError("line %d: invalid date" % line_number)
  year, month, day = date_digits.groups()
  year = year.zfill(4)[2:4]
  month = month.zfill(2)[:2]
  day = month.zfill(2)[:2]
  date = time.strptime(year + month + day, '%y%m%d')
  transaction.date = date

  transaction.description = line[date_digits.end(3):].strip()

  entry_lines = transaction_lines[1:]
  if not entry_lines:
    raise ParseError('line %d: no entry' % line_number)
  transaction.entries = map(_parse_entry, entry_lines)

  return transaction

def _parse_entry(entry_line):
  line_number, line = entry_line
  amount = re.search('(-?[0-9.]+)\s*$', line)
  if amount:
    amount_start = amount.start(1)
    amount = Decimal(amount.group(1))
    currency = re.search('\s+(.*?)$', line[:amount_start])
    currency_start = currency.start(1)
    currency = currency.group(1)
    account = line[:currency_start].strip()
  else:
    amount = None
    currency = None
    account = line.strip()
  return Entry(account, currency, amount, line_number)

def parse_transactions(transactions):
  return map(_parse_transaction, transactions)

def print_transactions(transactions):
  def format_transaction(transaction):
    ret = ''
    ret += time.strftime('%Y-%m-%d', transaction.date)
    ret += ' ' + transaction.description
    for entry in transaction.entries:
      ret += '\n' + entry.account.ljust(30, ' ')
      if entry.amount:
        ret += ' ' + entry.currency + str(entry.amount)
    return ret

  return '\n\n'.join(format_transaction(t) for t in transactions)

def calculate_balance(transactions):
  account_balances = {}
  for transaction in transactions:
    transaction_balance = {}
    omitted_account = None
    for entry in transaction.entries:
      if entry.amount:
        if entry.currency not in transaction_balance:
          transaction_balance[entry.currency] = Decimal(0)
        transaction_balance[entry.currency] += entry.amount
        if entry.account not in account_balances:
          account_balances[entry.account] = {}
        if entry.currency not in account_balances[entry.account]:
          account_balances[entry.account][entry.currency] = Decimal(0)
        account_balances[entry.account][entry.currency] += entry.amount
      elif omitted_account is None:
        omitted_account = entry.account
      else:
        raise ParseError("line %d: only one account can omit its amount" % entry.line_number)
    if omitted_account:
      for currency in transaction_balance:
        if transaction_balance[currency] != Decimal(0):
          if omitted_account not in account_balances:
            account_balances[omitted_account] = {}
          if currency not in account_balances[omitted_account]:
            account_balances[omitted_account][currency] = Decimal(0)
          account_balances[omitted_account][currency] += (Decimal(0) - transaction_balance[currency])
    else:
      for currency in transaction_balance:
        if transaction_balance[currency] != Decimal(0):
          raise ParseError("line %d: transaction not balance: %s%s" %
            (entry.line_number, currency, str(transaction_balance[currency])))

  return account_balances

def print_account_balance(account_balances):
  sorted_by_name = list(account_balances.iteritems())
  sorted_by_name.sort(lambda a, b: cmp(a[0], b[0]))
  ret = ''
  for account in sorted_by_name:
    account_name, currencies = account
    ret += account_name
    for currency in currencies:
      ret += ' ' + currency + str(currencies[currency])
    ret += '\n'
  return ret

def main():
  if len(sys.argv) < 1:
    print 'Usage: %s [LEDGER FILE] [COMMANDS]...' % sys.argv[0]
    sys.exit()

  ledger_file = sys.argv[1]
  commands = sys.argv[2:]
  if not commands:
    commands = [ # default commands
      read_file,
      split_transactions,
      parse_transactions,
      #print_transactions,
      calculate_balance,
      print_account_balance,
    ]

  result = ledger_file
  for command in commands:
    try:
      result = command(result)
    except ParseError, e:
      print 'Error: %s' % e.message
      sys.exit()

  print str(result)

if __name__ == '__main__':
  main()
