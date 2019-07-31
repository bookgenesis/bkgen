import os, sys, logging
from bl.rglob import rglob
from bgs import GS
from bmagick import Magick
from bkgen import config

magick = Magick(cmd=config.Images and config.Images.magick or 'gm')
gs = GS(magick=magick.cmd)


def trim(fn):
    """trim the file and return the output filename"""
    ext = os.path.splitext(fn)[-1].lower()
    if ext in ['.pdf', '.eps']:
        outfiles = gs.render(fn, outfn=os.path.splitext(fn)[0] + '.jpg', mogrify={'trim': ''})
        return '\n'.join(outfiles)
    else:
        magick.mogrify(fn, trim="")
        return fn


if __name__ == '__main__':
    logging.basicConfig(level=10)
    fns = []
    cmd = sys.argv[1]
    for path in sys.argv[2:]:
        if os.path.isdir(path):
            fns += rglob(path, "*.*")
        elif os.path.exists(path):
            fns += [path]
        else:
            raise ValueError("File not found: %s" % path)
    if cmd == 'trim':
        for fn in fns:
            print("trim:", trim(fn))
    else:
        raise ValueError('Unsupported command: %s' % cmd)
