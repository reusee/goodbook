#!/usr/bin/env python2
# coding: utf8

import sys
import re
import time

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
      transactions.append([line])
    else: # entry
      try:
        transactions[-1].append(line)
      except IndexError:
        raise Exception("line %d: invalid entry indentation" % line_number)
  return transactions

def parse_transactions(transactions):
  def parse_transaction(transaction_lines):
    transaction = {}

    splitted_first_line = transaction_lines[0].split(None, 1)

    date_string = splitted_first_line[0]
    date_digits = re.findall('[0-9]+', date_string)
    year, month, day = date_digits[:3]
    year = year.zfill(4)[2:4]
    month = month.zfill(2)[:2]
    day = month.zfill(2)[:2]
    date = time.strptime(year + month + day, '%y%m%d')
    transaction['year'] = year
    transaction['month'] = month
    transaction['day'] = day
    transaction['date'] = date

    transaction['description'] = splitted_first_line[1]

    return transaction

  return map(parse_transaction, transactions)

def print_transactions(transactions):
  def format_transaction(transaction):
    return ''.join([
      time.strftime('%Y-%m-%d', transaction['date']),
      ' ',
      transaction['description'],
    ])

  return '\n'.join(format_transaction(t) for t in transactions)

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
      print_transactions,
    ]

  result = ledger_file
  for command in commands:
    try:
      result = command(result)
    except Exception, e:
      print 'Error: %s' % e.message
      sys.exit()

  print str(result)

if __name__ == '__main__':
  main()
