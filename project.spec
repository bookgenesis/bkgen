# -*- mode: python -*-

block_cipher = None


a = Analysis(['bkgen/project.py'],
             pathex=['/Users/sah/bg/bkgen'],
             binaries=[],
             datas=[
              ('bkgen/__config__.ini', 'bkgen'),
              ('bkgen/converters/*.xsl', 'bkgen/converters'),
              ('bkgen/templates', 'bkgen/templates'),
              ('bkgen/resources/epubtypes.json', 'bkgen/resources'),
              ('bkgen/resources/mime.types', 'bkgen/resources'),
              ('bkgen/resources/epubcheck-4.0.2/epubcheck.jar', 'bkgen/resources/epubcheck-4.0.2'),
              ('bkgen/resources/KindleGen_Mac_i386_v2_9/kindlegen', 'bkgen/resources/KindleGen_Mac_i386_v2_9'),
             ],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='project',
          debug=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='project')
#app = BUNDLE(exe,
#         name='project.app',
#         icon=None,
#         bundle_identifier=None)
