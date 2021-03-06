#!/usr/bin/env python2
# coding: utf8

import sys
import re
import time
from decimal import *
import collections

class Transaction:
  def __init__(self):
    self.date = None
    self.description = None
    self.entries = None

class Entry:
  def __init__(self, account, currency, amount, line_number):
    self.account = account
    self.currency = currency
    self.amount = amount
    self.line_number = line_number

class ParseError(Exception): pass

class Ledger:
  def __init__(self, file_name):
    self.month_transactions = {}

    self.ledger = open(file_name, 'r').read()
    self.split_transactions()
    self.parse_transactions()

    self.account_balances = self.calculate_balance(self.transactions)

  def split_transactions(self):
    ledger = self.ledger.splitlines()
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
    self.transactions = transactions

  def _parse_transaction(self, transaction_lines):
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
    transaction.entries = map(self._parse_entry, entry_lines)

    year_month = year + '-' + month
    if year_month not in self.month_transactions:
      self.month_transactions[year_month] = []
    self.month_transactions[year_month].append(transaction)

    return transaction

  def _parse_entry(self, entry_line):
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

  def parse_transactions(self):
    self.transactions = map(self._parse_transaction, self.transactions)

  def _format_transaction(self, transaction):
    ret = ''
    ret += time.strftime('%Y-%m-%d', transaction.date)
    ret += ' ' + transaction.description
    for entry in transaction.entries:
      ret += '\n  ' + entry.account.ljust(30, ' ')
      if entry.amount:
        ret += ' ' + entry.currency + str(entry.amount)
    return ret

  def print_transactions(self, filter_func = None):
    if filter_func:
      transactions = filter(filter_func, self.transactions)
    else:
      transactions = self.transactions
    print '\n\n'.join(self._format_transaction(t) for t in transactions)

  def calculate_balance(self, transactions):
    account_balances = {}
    for transaction in transactions:
      transaction_balance = {}
      amount_omitted_entry = None
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
        elif amount_omitted_entry is None:
          amount_omitted_entry = entry
        else:
          raise ParseError("line %d: only one account can omit its amount" % entry.line_number)
      if amount_omitted_entry:
        omitted_account = amount_omitted_entry.account
        for currency in transaction_balance:
          if transaction_balance[currency] != Decimal(0):
            if omitted_account not in account_balances:
              account_balances[omitted_account] = {}
            if currency not in account_balances[omitted_account]:
              account_balances[omitted_account][currency] = Decimal(0)
            amount = Decimal(0) - transaction_balance[currency]
            account_balances[omitted_account][currency] += amount
            if not amount_omitted_entry.amount:
              amount_omitted_entry.amount = amount
              amount_omitted_entry.currency = currency
            else:
              transaction.entries.append(Entry(omitted_account, currency, amount, amount_omitted_entry.line_number))
      else:
        for currency in transaction_balance:
          if transaction_balance[currency] != Decimal(0):
            raise ParseError("line %d: transaction not balance: %s%s" %
              (entry.line_number, currency, str(transaction_balance[currency])))

    return account_balances

  def print_balance(self, balances):
    hierarchy = {}
    for account_str in balances:
      current_node = hierarchy
      account_balance = balances[account_str]
      account_str = account_str.decode('utf8')
      account = re.search(u'(.*?)[:：]', account_str, re.U)

      while account:
        account_name = account.group(1)
        if account_name not in current_node:
          current_node[account_name] = {'balance': {}, 'children': {}}
        for currency in account_balance:
          if currency not in current_node[account_name]['balance']:
            current_node[account_name]['balance'][currency] = Decimal(0)
          current_node[account_name]['balance'][currency] += account_balance[currency]
        current_node = current_node[account_name]['children']
        account_str = account_str[account.end(0):]
        account = re.search(u'(.*?)[:：]', account_str, re.U)

      if account_str:
        if account_str not in current_node:
          current_node[account_str] = {'balance': {}, 'children': {}}
        for currency in account_balance:
          if currency not in current_node[account_str]['balance']:
            current_node[account_str]['balance'][currency] = Decimal(0)
          current_node[account_str]['balance'][currency] += account_balance[currency]

    self.print_balance_hierarchy(hierarchy)

  @staticmethod
  def _sum_currency(account):
    factor = {
      '￥': 1,
      '$': 6.4,
    }
    total = 0.0
    for currency in account[1]['balance']:
      total += float(account[1]['balance'][currency]) * factor[currency]
    return abs(total)

  def print_balance_hierarchy(self, hierarchy, indent = 0, sort_currency = '￥'):
    sorted_balance = sorted(list(hierarchy.iteritems()),
      key = self._sum_currency, reverse = True)
    for account in sorted_balance:
      name, info = account
      s = ''
      for currency in info['balance']:
        if info['balance'][currency] != 0:
          s += ' ' + currency + str(info['balance'][currency])
      if s:
        print ' ' * 4 * indent + name, s
      if info['children']:
        self.print_balance_hierarchy(info['children'], indent + 1, sort_currency)

  def print_monthly_account_balance(self):
    for month in sorted(self.month_transactions.keys()):
      print month.center(50, '-')
      balance = self.calculate_balance(self.month_transactions[month])
      self.print_balance(balance)

def main():
  if len(sys.argv) < 1:
    print 'Usage: %s [LEDGER FILE] [COMMANDS]...' % sys.argv[0]
    sys.exit()

  ledger_file = sys.argv[1]
  ledger = Ledger(ledger_file)

  def _account_and_amount(transaction):
    for entry in transaction.entries:
      if '支出：' in entry.account and entry.currency == '￥' and entry.amount > Decimal(100):
        return True
    return False

  commands = sys.argv[2:]
  if commands:
    if commands[0].startswith('b'): # total balance
      ledger.print_balance(ledger.account_balances)
    elif commands[0].startswith('m'): # monthly balance
      ledger.print_monthly_account_balance()
    elif commands[0].startswith('p'): # print transaction
      ledger.print_transactions()
    elif commands[0].startswith('stat'):
      ledger.print_transactions(_account_and_amount)
  else:
    ledger.print_balance(ledger.account_balances)

if __name__ == '__main__':
  main()
