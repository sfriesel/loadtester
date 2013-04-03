
import sys, re

from operator import add

def parse_file(lines):
    data = {}
    itr = iter(lines)
    for names in itr:
        values = itr.next()
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

def diffs(d1s, d2s):
     return dict((node, diff(d1, d2s[node])) for node, d1 in d1s.iteritems())

def reducedata(op, ds):
    return reduce((lambda d1, d2: mapdata(op, d1, d2)), ds)

def sumdata(ds):
    return reducedata(add, ds)

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

def pretty_print(diffd, d1, d2, dmin, dmax):
    for cat, vals in diffd.iteritems():
        print cat
        for name, val in sorted(vals.iteritems()):
            if not val == 0:
                print '   %s %s (%s) min: %s max: %s' % (name,
                                                         readable(val, True),
                                                         readable(d1[cat][name]),
                                                         readable(dmin[cat][name]),
                                                         readable(dmax[cat][name]))


def parse_files(s):
    data = {}
    for f in re.split("\n\n+", s.rstrip('\n')):
        lines = f.split('\n')
        data[lines[0]] = parse_file(lines[1:])
    return data

if sys.argv[1] == '--multiple':

    paths = sys.argv[2:]

    datas = [parse_file(open(path)) for path in paths]

    midpoint = len(datas) / 2

    s1s = dict(zip(xrange(midpoint), datas[:midpoint]))
    s2s = dict(zip(xrange(midpoint), datas[midpoint:]))

else:

    with open(sys.argv[1]) as f:
        data = f.read()

    before, after = data.split('-' * 69 + '\n')

    s1s = parse_files(before)
    s2s = parse_files(after)

s1 = sumdata(s1s.values())
s2 = sumdata(s2s.values())

dfs = diffs(s1s, s2s)

smin = reducedata(min, dfs.values())
smax = reducedata(max, dfs.values())

pretty_print(sumdata(dfs.values()), s1, s2, smin, smax)
