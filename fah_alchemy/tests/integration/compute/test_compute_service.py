import pytest

from pathlib import Path

from fah_alchemy.compute.service import SynchronousComputeService


class TestSynchronousComputeService:
    ...

    
    @pytest.fixture
    def service(self, n4js_preloaded, compute_client, tmpdir):
        with tmpdir.as_cwd():
            return SynchronousComputeService(
                    api_url=compute_client.api_url,
                    identifier=compute_client.identifier,
                    key=compute_client.key,
                    name='test_compute_service',
                    shared_path=Path('.').absolute())

    def test_get_task(self, service):

        service.get_tasks()
        ...
