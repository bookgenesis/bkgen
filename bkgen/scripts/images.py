
import os, sys
from bl.rglob import rglob
from bgs import GS
from bmagick import Magick
from bkgen import config

magick = Magick(cmd=config.Images and config.Images.magick or 'gm')
gs = GS(magick=magick.cmd)


def trim(fn):
    """trim the file and return the output filename"""
    ext = os.path.splitext(fn)[-1].lower
    if ext in ['.pdf', '.eps']:
        outfiles = gs.render(mogrify={'trim': ''})
        return '\n'.join(outfiles)
    else:
        magick.mogrify(fn, trim="")
        return fn


if __name__ == '__main__':
    fns = []
    cmd = sys.argv[1]
    for path in sys.argv[2:]:
        if os.path.isdir(path):
            fns += rglob(path, "*.*")
        else:
            fns += [path]
    if cmd == 'trim':
        for fn in fns:
            print("trim:", trim(fn))
    else:
        raise ValueError('Unsupported command: %s' % cmd)
