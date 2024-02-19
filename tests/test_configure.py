from src.ss.configure.configure import Configure
from src.ss.configure.unit import Unit
from .fixtures import config 

class TestConfigure:
    def test_source(self, config):
        config = Configure(config)
        assert config.sources['units'].name == 'units'
        assert config.sources['units'].value == 'latest'
    
    def test_metadata(self, config):
        config = Configure(config)
        assert config.metadata.name == 'test project'
        assert config.metadata.version == '0.0.1'
        assert config.metadata.description == 'project description'

    def test_get_units(self, config):
       pass 
