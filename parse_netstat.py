
import sys

from operator import add


def parse_file(path):
    f = open(path)
    data = {}
    for names in f:
        values = f.next()
        names_parsed = names.rstrip().split(" ")
        category = names_parsed[0]
        names_parsed = names_parsed[1:]
        values_parsed = [int(i) for i in values.rstrip().split(" ")[1:]]
        data[category] = dict(zip(names_parsed, values_parsed))
    return data

def mapdata(op, d1, d2):
    return dict((cat, dict((name, op(val, d2.get(cat, {}).get(name, 0)))
                           for name, val in vals.iteritems()))
                for cat, vals in d1.iteritems())

def diff(d1, d2):
    return mapdata((lambda x, y: y - x), d1, d2)

def sumdata(ds):
    return reduce((lambda d1, d2: mapdata(add, d1, d2)), ds)

def readable(x, show_sign=False):
    work = str(abs(x))
    res = ''
    while len(work) > 4:
        res = ',' + work[-3:] + res
        work = work[:-3]
    res = work + res
    if show_sign:
        if x < 0:
            res = '-' + res
        else:
            res = '+' + res
    return res

def pretty_print(diffd, d1, d2):
    for cat, vals in diffd.iteritems():
        print cat
        for name, val in sorted(vals.iteritems()):
            if not val == 0:
                print '   %s %s (%s)' % (name, readable(val, True),
                                         readable(d1[cat][name]))

paths = sys.argv[1:]

datas = [parse_file(path) for path in paths]

midpoint = len(datas) / 2

s1 = sumdata(datas[:midpoint])
s2 = sumdata(datas[midpoint:])

pretty_print(diff(s1, s2), s1, s2)
