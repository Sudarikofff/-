import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from apply_update import apply


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.source=Path(self.temp.name)/'source'; self.source.mkdir()
        self.target=Path(self.temp.name)/'target'; self.target.mkdir()
        (self.source/'main.py').write_text('new')
        (self.target/'main.py').write_text('old')
        (self.source/'new.py').write_text('added')
        files={}
        for name, old, new in [('main.py','old','new'),('new.py',None,'added')]:
            files[name]=dict(old_sha256=hashlib.sha256(old.encode()).hexdigest() if old else None,
                             new_sha256=hashlib.sha256(new.encode()).hexdigest())
        (self.source/'update-manifest.json').write_text(json.dumps({'files':files}))
        (self.target/'database').mkdir()
        (self.target/'database/discipline.db').write_bytes(b'preserve database')

    def tearDown(self): self.temp.cleanup()

    def test_install_preserves_database_backs_up_and_is_repeatable(self):
        apply(self.source,self.target)
        self.assertEqual((self.target/'main.py').read_text(),'new')
        self.assertEqual((self.target/'new.py').read_text(),'added')
        self.assertEqual((self.target/'database/discipline.db').read_bytes(),b'preserve database')
        backups=list((self.target/'backup').glob('*/main.py'))
        self.assertEqual(len(backups),1)
        self.assertEqual(backups[0].read_text(),'old')
        apply(self.source,self.target)
        self.assertEqual(len(list((self.target/'backup').glob('*/main.py'))),1)

    def test_conflict_changes_nothing(self):
        (self.target/'main.py').write_text('new work by user')
        with self.assertRaises(ValueError): apply(self.source,self.target)
        self.assertEqual((self.target/'main.py').read_text(),'new work by user')
        self.assertFalse((self.target/'new.py').exists())
        self.assertFalse((self.target/'backup').exists())

    def test_partial_failure_restores_prior_files(self):
        replace=Path.replace
        def fail_second(path,destination):
            if str(destination).endswith('new.py'): raise OSError('simulated write error')
            return replace(path,destination)
        with patch.object(Path,'replace',fail_second):
            with self.assertRaises(OSError): apply(self.source,self.target)
        self.assertEqual((self.target/'main.py').read_text(),'old')
        self.assertFalse((self.target/'new.py').exists())
        self.assertFalse(list(self.target.glob('.profile-update-*')))


if __name__=='__main__': unittest.main()
