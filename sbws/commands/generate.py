from sbws.globals import (fail_hard, is_initted)
from argparse import ArgumentDefaultsHelpFormatter
from statistics import median
import os
import json
import time


def read_result_file(fname, starting_dict=None):
    data = starting_dict if starting_dict else {}
    with open(fname, 'rt') as fd:
        for line in fd:
            d = json.loads(line)
            fp = d['fingerprint']
            if fp not in data:
                data[fp] = []
            data[fp].append(d)
    return data


class V3BWLine:
    def __init__(self, fp, bw, nick, rtts):
        self.fp = fp
        self.bw = bw
        self.nick = nick
        # convert to ms
        rtts = [round(r * 1000) for r in rtts]
        self.rtt = round(median(rtts))

    def __str__(self):
        frmt = 'node_id={fp} bw={sp} nick={n} rtt={rtt}'
        return frmt.format(fp=self.fp, sp=round(self.bw), n=self.nick,
                           rtt=self.rtt)


def result_data_to_v3bw_line(data, fingerprint):
    assert fingerprint in data
    results = data[fingerprint]
    nick = results[0]['nickname']
    speeds = [dl['amount'] / dl['duration']
              for r in results for dl in r['downloads']]
    speed = median(speeds)
    rtts = [rtt for r in results for rtt in r['rtts']]
    return V3BWLine(fingerprint, speed, nick, rtts)


def scale_lines(v3bw_lines, scale_max):
    total = sum([l.bw for l in v3bw_lines])
    ratio = scale_max / total
    for line in v3bw_lines:
        line.bw = round(line.bw * ratio)
    return v3bw_lines


def gen_parser(sub):
    p = sub.add_parser('generate',
                       formatter_class=ArgumentDefaultsHelpFormatter)
    p.add_argument('--result-directory', default='dd', type=str,
                   help='Where result data from the sbws client is stored')
    p.add_argument('--output', default='/dev/stdout', type=str,
                   help='Where to write v3bw file')
    p.add_argument('--scale-max', default=50000000, type=int,
                   help='When scaling bw weights, scale them up/down '
                   'as if this is the sum of all measurements')


def main(args, log_):
    global log
    log = log_
    if not is_initted(os.getcwd()):
        fail_hard('Directory isn\'t initted')
    if not os.path.isdir(args.result_directory):
        fail_hard(args.result_directory, 'does not exist')

    data_fnames = sorted(os.listdir(args.result_directory), reverse=True)
    data_fnames = data_fnames[0:14]
    data_fnames = [os.path.join(args.result_directory, f) for f in data_fnames]
    data = {}
    for fname in data_fnames:
        data = read_result_file(fname, data)
    data_lines = [result_data_to_v3bw_line(data, fp) for fp in data]
    data_lines = sorted(data_lines, key=lambda d: d.bw, reverse=True)
    data_lines = scale_lines(data_lines, args.scale_max)
    with open(args.output, 'wt') as fd:
        fd.write('{}\n'.format(int(time.time())))
        for line in data_lines:
            fd.write('{}\n'.format(str(line)))
