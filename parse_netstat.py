
import sys


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

def diff(d1, d2):
    return dict((cat, dict((name, d2[cat][name] - val)
                           for name, val in vals.iteritems()))
                for cat, vals in d1.iteritems())

def readable(x, show_sign=False):
    work = str(abs(x))
    res = ''
    while len(work) > 4:
        res = ' ' + work[-3:] + res
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
        for name, val in vals.iteritems():
            if not val == 0:
                print '   %s %s (%s)' % (name, readable(val, True), readable(d1[cat][name]))

s1 = parse_file(sys.argv[1])
s2 = parse_file(sys.argv[2])

pretty_print(diff(s1, s2), s1, s2)
