#!/usr/bin/env python

from shlex import shlex

def vdf2json(stream):

    """
    Read a Steam vdf file and return a string in json format
    """

    def _istr(ident, string):
        return (ident * '  ') + string

    jbuf = '{\n'
    lex = shlex(stream)
    indent = 1

    while True:
        tok = lex.get_token()
        if not tok:
            return jbuf + '}\n'
        if tok == '}':
            indent -= 1
            jbuf += _istr(indent, '}')
            ntok = lex.get_token()
            lex.push_token(ntok)
            if ntok and ntok != '}':
                jbuf += ','
            jbuf += '\n'
        else:
            ntok = lex.get_token()
            if ntok == '{':
                jbuf += _istr(indent, tok + ': {\n')
                indent += 1
            else:
                jbuf += _istr(indent, tok + ': ' + ntok)
                ntok = lex.get_token()
                lex.push_token(ntok)
                if ntok != '}':
                    jbuf += ','
                jbuf += '\n'
def main():
    """
    Read Steam vdf and write json compatible conversion
    """
    import sys
    import argparse

    parser = argparse.ArgumentParser(prog='vdf2json', description=main.__doc__)
    parser.add_argument('-i', '--input',
                        default=sys.stdin,
                        type=argparse.FileType('r'),
                        help='input vdf file (stdin if not specified)')
    parser.add_argument('-o', '--output',
                        default=sys.stdout,
                        type=argparse.FileType('w'),
                        help='output json file (stdout if not specified)')

    args = parser.parse_args()
    args.output.write(vdf2json(args.input))

if __name__ == '__main__':
    main()
