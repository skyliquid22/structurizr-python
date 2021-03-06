# Copyright (c) 2020, Moritz E. Beber.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Ensure correct workspace (de-)serialization."""


import json
from importlib import import_module
from pathlib import Path

import pytest
from pydantic import ValidationError

from structurizr import Workspace, WorkspaceIO


DEFINITIONS = Path(__file__).parent / "data" / "workspace_definition"
EXAMPLES = Path(__file__).parent.parent.parent / "examples"
VALIDATIONS = Path(__file__).parent / "data" / "workspace_validation"


def pytest_generate_tests(metafunc) -> None:
    """Generate test parameters for invalid workspace tests."""
    if "invalid_workspace" in metafunc.fixturenames:
        files = sorted(Path("data", "workspace_validation").glob("*.json"))
        ids = [p.name for p in files]
        metafunc.parametrize(
            "invalid_workspace",
            [
                pytest.param(f, marks=pytest.mark.raises(exception=ValidationError))
                for f in files
            ],
            ids=ids,
        )


def test_invalid_workspace(invalid_workspace):
    """
    Test that invalid workspaces raise ValidationError.

    Note that the parameterisation of this test, including that it raises a vaalidation
    error is controlled through `pytest_generate_tests`.
    """
    WorkspaceIO.parse_file(invalid_workspace)


@pytest.mark.parametrize(
    "filename",
    ["Trivial.json", "GettingStarted.json", "FinancialRiskSystem.json", "BigBank.json"],
)
def test_deserialize_workspace(filename):
    """Expect that a trivial workspace definition is successfully deserialized."""
    path = DEFINITIONS / filename
    Workspace.load(path)


@pytest.mark.parametrize(
    "example, filename",
    [
        ("getting_started", "GettingStarted.json"),
    ],
)
def test_serialize_workspace(example, filename, monkeypatch):
    """Expect that ."""
    monkeypatch.syspath_prepend(EXAMPLES)
    example = import_module(example)
    path = DEFINITIONS / filename
    # TODO (midnighter): Use `from_orm` like `.construct` bypassing validation. (
    #  Requires a pull request on pydantic.)
    expected = WorkspaceIO.from_orm(Workspace.load(path))
    actual = WorkspaceIO.from_orm(example.main())
    assert json.loads(actual.json()) == json.loads(expected.json())
    # TODO (Midnighter): This should be equivalent to the above. Why is it not?
    #  Is `.json` not using the same default arguments as `.dict`?
    # assert actual.dict() == expected.dict()


def test_save_and_load_workspace_to_string(monkeypatch):
    """Test saving as a JSON string and reloading."""
    monkeypatch.syspath_prepend(EXAMPLES)
    example = import_module("getting_started")
    workspace = example.main()

    json_string: str = workspace.dumps(indent=2)
    workspace2 = Workspace.loads(json_string)

    expected = WorkspaceIO.from_orm(workspace)
    actual = WorkspaceIO.from_orm(workspace2)
    assert json.loads(actual.json()) == json.loads(expected.json())


def test_load_workspace_from_bytes(monkeypatch):
    """Test loading from bytes rather than string."""
    path = DEFINITIONS / "GettingStarted.json"
    with open(path, mode="rb") as file:
        binary_content = file.read()

    workspace = Workspace.loads(binary_content)

    assert workspace.model.software_systems != set()


def test_save_and_load_workspace_to_file(monkeypatch, tmp_path: Path):
    """Test saving as a JSON file and reloading."""
    monkeypatch.syspath_prepend(EXAMPLES)
    example = import_module("getting_started")
    workspace = example.main()

    filepath = tmp_path / "test_workspace.json"

    workspace.dump(filepath, indent=2)
    workspace2 = Workspace.load(filepath)

    expected = WorkspaceIO.from_orm(workspace)
    actual = WorkspaceIO.from_orm(workspace2)
    assert json.loads(actual.json()) == json.loads(expected.json())


def test_save_and_load_workspace_to_gzipped_file(monkeypatch, tmp_path: Path):
    """Test saving as a zipped JSON file and reloading."""
    monkeypatch.syspath_prepend(EXAMPLES)
    example = import_module("getting_started")
    workspace = example.main()

    filepath = tmp_path / "test_workspace.json.gz"

    workspace.dump(filepath)
    workspace2 = Workspace.load(filepath)

    expected = WorkspaceIO.from_orm(workspace)
    actual = WorkspaceIO.from_orm(workspace2)
    assert json.loads(actual.json()) == json.loads(expected.json())


def test_workspace_overridding_zip_flag(monkeypatch, tmp_path: Path):
    """Test that default zipping can be overridden explicitly."""
    monkeypatch.syspath_prepend(EXAMPLES)
    example = import_module("getting_started")
    workspace = example.main()

    filepath = tmp_path / "test_workspace.json.gz"

    workspace.dump(filepath, zip=False)
    contents = filepath.read_text()
    assert "My software system" in contents

    # Make sure can be loaded even though its not zipped and ends with .gz
    Workspace.load(filepath)


def test_load_unknown_file_raises_file_not_found():
    """Test that attempting to load a non-existent file raises FileNotFound."""
    with pytest.raises(FileNotFoundError):
        Workspace.load("foobar.json")
