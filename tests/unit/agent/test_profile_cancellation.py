"""Cancellation contract tests shared by implemented profiles."""

from __future__ import annotations

import pytest
from cloudeyes_agent.execution import CancellationRequested, CancellationToken
from cloudeyes_agent.profiles.compute import ComputeProfileConfig, run_compute_profile
from cloudeyes_agent.profiles.database import DatabaseProfileConfig, run_database_profile
from cloudeyes_agent.profiles.general import GeneralProfileConfig, run_general_profile
from cloudeyes_agent.profiles.networking import (
    NetworkingProfileConfig,
    run_networking_profile,
)
from cloudeyes_agent.profiles.storage import StorageProfileConfig, run_storage_profile
from cloudeyes_agent.profiles.web import WebProfileConfig, run_web_profile

from tests.unit.agent.test_discovery_models import make_result


@pytest.mark.parametrize(
    "runner, config",
    (
        (run_general_profile, GeneralProfileConfig.quick()),
        (run_storage_profile, StorageProfileConfig.quick()),
        (run_networking_profile, NetworkingProfileConfig.quick()),
        (run_compute_profile, ComputeProfileConfig.quick(workers=1)),
        (run_web_profile, WebProfileConfig.quick()),
        (run_database_profile, DatabaseProfileConfig.quick()),
    ),
)
def test_profile_propagates_pre_requested_cancellation(runner, config) -> None:
    token = CancellationToken.local()
    token.request_cancellation()

    with pytest.raises(CancellationRequested):
        runner(
            config=config,
            discovery=make_result(),
            cancellation_token=token,
        )
