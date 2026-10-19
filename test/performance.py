#!/usr/bin/env python3
"""Optional scaling benchmarks: python3 test/performance.py /path/to/nixfmt.

Reports wall time, CPU time and peak RSS on Unix. Run against both revisions
on the same machine; these are measurements, not timing-sensitive CI tests.
Each input is also checked for parse preservation and formatting idempotence.
"""

import argparse
import json
import os
import tempfile
import time


def path(n):
    return './' + '/'.join(['a'] * n) + '\n'


CASES = {'path': path}


def run(binary, source, verify=False):
    with tempfile.TemporaryFile() as stdin, tempfile.TemporaryFile() as stderr:
        stdin.write(source.encode())
        stdin.seek(0)
        start = time.monotonic()
        pid = os.fork()
        if pid == 0:
            os.dup2(stdin.fileno(), 0)
            os.dup2(os.open(os.devnull, os.O_WRONLY), 1)
            os.dup2(stderr.fileno(), 2)
            args = [binary, '-']
            if verify:
                args.append('--verify')
            os.execv(binary, args)
        _, status, usage = os.wait4(pid, 0)
        elapsed = time.monotonic() - start
        if status:
            stderr.seek(0)
            raise RuntimeError(stderr.read().decode())
        return {'seconds': elapsed, 'cpu_seconds': usage.ru_utime + usage.ru_stime,
                'max_rss': usage.ru_maxrss}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary', type=os.path.abspath)
    parser.add_argument('--case', choices=CASES, action='append')
    parser.add_argument('--sizes', type=int, nargs='+', default=[10000, 20000, 40000, 80000])
    args = parser.parse_args()
    for name in args.case or CASES:
        for n in args.sizes:
            source = CASES[name](n)
            result = run(args.binary, source)
            run(args.binary, source, verify=True)
            print(json.dumps(dict(case=name, n=n, **result)), flush=True)


if __name__ == '__main__':
    main()
