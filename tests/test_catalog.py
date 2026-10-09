import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from catalog import Catalog, selection

class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.base=Path(self.temp.name)
        (self.base/'prefill').mkdir()
        (self.base/'prefill-meta/v1').mkdir(parents=True)
        self.select([322330,526870])
        with patch('catalog.threading.Thread'):
            self.catalog=Catalog(self.base)
        self.catalog.names={'322330':{'name':"Don't Starve Together",'checkedAt':10**12,'ok':True}}

    def tearDown(self): self.temp.cleanup()
    def select(self,ids): (self.base/'prefill/selectedAppsToPrefill.json').write_text(json.dumps(ids))
    def manifest(self,name,stamp):
        p=self.base/'prefill-meta/v1'/name
        p.write_bytes(b'')
        os.utime(p,ns=(stamp,stamp))

    def test_selection_changes_are_visible_without_restart(self):
        self.assertEqual([g['id'] for g in self.catalog.games()],[322330,526870])
        self.select([892970])
        self.assertEqual([g['id'] for g in self.catalog.games()],[892970])

    def test_empty_selection_does_not_restore_presets(self):
        self.select([])
        self.assertEqual(self.catalog.games(),[])

    def test_invalid_selection_is_not_silently_reported_as_empty(self):
        for ids in [[True],[0],['526870'],{'id':526870}]:
            self.select(ids)
            with self.assertRaises(ValueError): selection(self.base)

    def test_unobserved_game_has_no_invented_cache_or_size_status(self):
        game=self.catalog.games()[0]
        self.assertEqual(game['status'],'unknown')
        self.assertFalse(game['filled'])
        self.assertIsNone(game['size'])

    def test_old_success_does_not_mark_new_manifest_prepared(self):
        self.manifest('322330_322330_322331_10.bin',100)
        self.manifest('322330_322330_322331_20.bin',200)
        (self.base/'prefill/successfullyDownloadedDepots.json').write_text('{"322331":[10]}')
        self.assertFalse(self.catalog.games()[0]['filled'])

    def test_all_observed_depots_required_for_prepared(self):
        self.manifest('322330_322330_322331_10.bin',100)
        self.manifest('322330_999999_322332_20.bin',100)
        p=self.base/'prefill/successfullyDownloadedDepots.json'
        p.write_text('{"322331":[10]}')
        self.assertEqual(self.catalog.games()[0]['status'],'partial')
        p.write_text('{"322331":[10],"322332":["20"]}')
        self.assertEqual(self.catalog.games()[0]['status'],'prepared')

    def test_only_current_active_game_gets_running_status(self):
        games=self.catalog.games(active=True,checking=True,logs='Starting Satisfactory\nStarting Don\'t Starve Together')
        self.assertEqual(games[0]['status'],'checking')
        self.assertEqual(games[1]['status'],'unknown')
        self.assertEqual(self.catalog.games(logs="Starting Don't Starve Together")[0]['status'],'unknown')

    def test_manifest_failure_is_shown_for_affected_game_only(self):
        games=self.catalog.games(logs="Starting Don't Starve Together\nUnable to download manifests! Skipping app...\nStarting Satisfactory")
        self.assertEqual(games[0]['status'],'failed')
        self.assertEqual(games[1]['status'],'unknown')

if __name__=='__main__': unittest.main()
