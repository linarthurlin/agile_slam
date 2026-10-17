"""Regression coverage for Windows-to-WSL simulation fixture forwarding."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('agile_deploy',Path(__file__).resolve().parents[1]/'scripts/deploy.py')
deploy=importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)


class WslGuiCommandTests(unittest.TestCase):
    def test_pose_is_forwarded_as_literal_environment_arguments(self):
        with patch.dict(deploy.os.environ,{'AGILE_SPAWN_X':'30','AGILE_SPAWN_Y':'-2','AGILE_SPAWN_YAW':'1.57'},clear=True):
            command=deploy.wsl_gui_command('Ubuntu-22.04','/mnt/d/Project With Spaces/scripts/deploy.py')
        self.assertEqual(command,['wsl','-d','Ubuntu-22.04','--','env','AGILE_SPAWN_X=30','AGILE_SPAWN_Y=-2','AGILE_SPAWN_YAW=1.57','python3','/mnt/d/Project With Spaces/scripts/deploy.py','up','--gui'])

    def test_unset_pose_is_explicitly_zero(self):
        with patch.dict(deploy.os.environ,{},clear=True):
            command=deploy.wsl_gui_command('Ubuntu-22.04','/project/deploy.py')
        self.assertEqual(command[5:8],['AGILE_SPAWN_X=0','AGILE_SPAWN_Y=0','AGILE_SPAWN_YAW=0'])

    def test_gpu_headless_forwarding_preserves_pose_and_rendering(self):
        with patch.dict(deploy.os.environ,{'AGILE_SPAWN_X':'30'},clear=True):
            command=deploy.wsl_up_command('Ubuntu-22.04','/project/deploy.py',False,'gpu')
        self.assertIn('AGILE_SPAWN_X=30',command)
        self.assertEqual(command[-3:],['up','--rendering','gpu'])
        self.assertNotIn('--gui',command)


if __name__=='__main__':
    unittest.main()
