import tempfile,unittest
from pathlib import Path
from package_release import release_files
class ReleaseTests(unittest.TestCase):
 def test_local_work_and_retired_experiments_never_enter_release(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder)
   paths=['app.py','semantic_scene.py','video/src/semantic.tsx','video/package-lock.json','web/template-previews/one.jpg','.backups/web/app.js','video/node_modules/one.js','video/output/frame.png','data/user/project.json','outputs/private.pdf','__pycache__/native_motion.pyc','native_motion.py','app.py.bak.20261025','render.log','.env','private.zip']
   for name in paths:
    p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('fixture')
   actual={p.relative_to(root).as_posix() for p in release_files(root)}
   self.assertEqual(actual,set(paths[:5]))
if __name__=='__main__':unittest.main()
