"""Test collection."""

import datetime
import os
import shlex
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner
from cookiecutter.utils import rmtree

if sys.version_info > (3, 0):
    import importlib
else:
    import imp


@pytest.fixture()
def cookiecutter_toplevel_files():
    not_present_at_default = ["LICENSE"]
    template_repo = Path("{{cookiecutter.repo_name}}")
    files = [p.name for p in template_repo.iterdir() if p.name not in not_present_at_default]
    return files


@contextmanager
def inside_dir(dirpath):
    """
    Execute code from inside the given directory
    :param dirpath: String, path of the directory the command is being run.
    """
    old_path = os.getcwd()
    try:
        os.chdir(dirpath)
        yield
    finally:
        os.chdir(old_path)


@contextmanager
def bake_in_temp_dir(cookies, *args, **kwargs):
    """
    Delete the temporal directory that is created when executing the tests
    :param cookies: pytest_cookies.Cookies,
        cookie to be baked and its temporal files will be removed
    """
    result = cookies.bake(*args, **kwargs)
    try:
        yield result
    finally:
        rmtree(str(result.project))


def run_inside_dir(command, dirpath):
    """
    Run a command from inside a given directory, returning the exit status
    :param command: Command that will be executed
    :param dirpath: String, path of the directory the command is being run.
    """
    with inside_dir(dirpath):
        return subprocess.check_call(shlex.split(command))


def check_output_inside_dir(command, dirpath):
    "Run a command from inside a given directory, returning the command output"
    with inside_dir(dirpath):
        return subprocess.check_output(shlex.split(command))


@pytest.mark.parametrize(
    "license",
    [
        "MIT License",
        "BSD License",
        "ISC License",
        "Apache Software License 2.0",
        "GNU General Public License v3.0",
    ],
)
def test_year_compute_in_license_file(cookies, license: str):
    with bake_in_temp_dir(cookies, extra_context={"open_source_license": license}) as result:
        license_file_path = result.project.join("LICENSE")
        y = str(datetime.datetime.now().year)
        if license == "GNU General Public License v3.0":
            y = "2007"
        assert y in license_file_path.read()


def project_info(result):
    """Get toplevel dir, package_name, and project dir from baked cookies"""
    project_repository = Path(str(result.project))
    package_name = project_repository.name.replace("-", "_")
    project_dir = project_repository.joinpath("src", package_name)
    return project_repository, package_name, project_dir


def test_bake_with_defaults(cookies, cookiecutter_toplevel_files):
    with bake_in_temp_dir(cookies) as result:
        assert result.project_path.is_dir()
        assert result.exit_code == 0
        assert result.exception is None
        found_toplevel_files = [f.basename for f in result.project.listdir()]
        for f in cookiecutter_toplevel_files:
            assert f in found_toplevel_files


# NOTE: for tests we use pytest
# def test_bake_and_run_tests(cookies):
#     with bake_in_temp_dir(cookies) as result:
#         assert result.project_path.is_dir()
#         run_inside_dir("python setup.py test", str(result.project)) == 0
#         print("test_bake_and_run_tests path", str(result.project))


def test_bake_withspecialchars_and_run_tests(cookies):
    """Ensure that a `full_name` with double quotes does not break setup.py"""
    with bake_in_temp_dir(
        cookies,
        extra_context={
            "full_name": 'name "quote" name',
            "email": "name@name.test",
            "author": 'name "quote" name',
        },
    ) as result:
        assert result.project_path.is_dir()
        run_inside_dir("python setup.py test", str(result.project)) == 0


def test_bake_with_apostrophe_and_run_tests(cookies):
    """Ensure that a `full_name` with apostrophes does not break setup.py"""
    with bake_in_temp_dir(
        cookies,
        extra_context={
            "full_name": "O'name",
            "author": "O'name",
            "email": "name@name.test",
        },
    ) as result:
        assert result.project_path.is_dir()
        run_inside_dir("python setup.py test", str(result.project)) == 0


# def test_bake_and_run_travis_pypi_setup(cookies):
#     # given:
#     with bake_in_temp_dir(cookies) as result:
#         project_path = str(result.project)
#
#         # when:
#         travis_setup_cmd = ('python travis_pypi_setup.py'
#                             ' --repo audreyr/cookiecutter-pypackage --password invalidpass')
#         run_inside_dir(travis_setup_cmd, project_path)
#         # then:
#         result_travis_config = yaml.load(result.project.join(".travis.yml").open())
#         min_size_of_encrypted_password = 50
#         assert len(result_travis_config["deploy"]["password"]["secure"]) > min_size_of_encrypted_password


def test_bake_without_travis_pypi_setup(cookies):
    with bake_in_temp_dir(cookies, extra_context={"use_pypi_deployment_with_travis": "n"}) as result:
        result_travis_config = yaml.safe_load(result.project.join(".travis.yml").open())
        assert "deploy" not in result_travis_config
        assert "python" == result_travis_config["language"]
        found_toplevel_files = [f.basename for f in result.project.listdir()]


def test_bake_without_author_file(cookies):
    with bake_in_temp_dir(cookies, extra_context={"create_author_file": "n"}) as result:
        found_toplevel_files = [f.basename for f in result.project.listdir()]
        assert "AUTHORS.rst" not in found_toplevel_files
        doc_files = [f.basename for f in result.project.join("docs").listdir()]
        assert "authors.rst" not in doc_files

        # Assert there are no spaces in the toc tree
        docs_index_path = result.project.join("docs/source/index.rst")
        with open(str(docs_index_path)) as index_file:
            assert "dependencies_graph\n   \nIndices" in index_file.read()

        # NOTE: Currently not using MANIFEST.in
        # # Check that
        # manifest_path = result.project.join("MANIFEST.in")
        # with open(str(manifest_path)) as manifest_file:
        #     assert "AUTHORS.rst" not in manifest_file.read()


# NOTE: Currently not using Makefile
# def test_make_help(cookies):
#     with bake_in_temp_dir(cookies) as result:
#         output = check_output_inside_dir("make help", str(result.project))
#         assert b"check code coverage quickly with the default Python" in output


@pytest.mark.parametrize(
    "license",
    [
        "MIT License",
        "BSD License",
        "ISC License",
        "Apache Software License 2.0",
        "GNU General Public License v3.0",
    ],
)
def test_bake_selecting_license(cookies, license):
    with bake_in_temp_dir(cookies, extra_context={"open_source_license": license}) as result:
        assert license in result.project.join("pyproject.toml").read()
        if license == "GNU General Public License v3.0":
            license = "GNU GENERAL PUBLIC LICENSE"
        assert license in result.project.join("LICENSE").read()


def test_bake_not_open_source(cookies):
    with bake_in_temp_dir(cookies, extra_context={"open_source_license": "Not open source"}) as result:
        found_toplevel_files = [f.basename for f in result.project.listdir()]
        assert "setup.py" in found_toplevel_files
        assert "LICENSE" not in found_toplevel_files
        assert "License" not in result.project.join("README.md").read()


def test_using_pytest(cookies):
    with bake_in_temp_dir(cookies, extra_context={"author": "author", "email": "mail@mail.test"}) as result:
        assert result.project_path.is_dir()
        test_file_path = result.project.join("tests/test_python_boilerplate.py")
        lines = test_file_path.readlines()
        assert "import pytest" in "".join(lines)
        # Test the new pytest target
        try:
            run_inside_dir("pytest", str(result.project)) == 0
        except subprocess.CalledProcessError:
            print("Failed to run pytest, probably due to a missing module. Retry.")
            run_inside_dir("pip install -e .", str(result.project))
            run_inside_dir("pytest", str(result.project)) == 0


def test_not_using_pytest(cookies):
    with bake_in_temp_dir(cookies, extra_context={"use_pytest": "n"}) as result:
        assert result.project_path.is_dir()
        test_file_path = result.project.join("tests/test_python_boilerplate.py")
        lines = test_file_path.readlines()
        assert "import unittest" in "".join(lines)
        assert "import pytest" not in "".join(lines)


# def test_project_with_hyphen_in_module_name(cookies):
#     result = cookies.bake(extra_context={'project_name': 'something-with-a-dash'})
#     assert result.project is not None
#     project_path = str(result.project)
#
#     # when:
#     travis_setup_cmd = ('python travis_pypi_setup.py'
#                         ' --repo audreyr/cookiecutter-pypackage --password invalidpass')
#     run_inside_dir(travis_setup_cmd, project_path)
#
#     # then:
#     result_travis_config = yaml.safe_load(open(os.path.join(project_path, ".travis.yml")))
#     assert "secure" in result_travis_config["deploy"]["password"],\
#         "missing password config in .travis.yml"


def test_bake_with_no_console_script(cookies):
    context = {"command_line_interface": "No command-line interface"}
    result = cookies.bake(
        extra_context=context,
    )
    project_path, package_name, project_dir = project_info(result)
    assert package_name == "python_boilerplate"
    found_project_files = os.listdir(project_dir)
    assert "cli.py" not in found_project_files

    setup_path = os.path.join(project_path, "setup.py")
    with open(setup_path, "r") as setup_file:
        assert "entry_points" not in setup_file.read()


def test_bake_with_console_script_files(cookies):
    result = cookies.bake()
    project_path, package_name, project_dir = project_info(result)
    assert package_name == "python_boilerplate"
    found_project_files = os.listdir(project_dir)
    assert "cli.py" in found_project_files

    pyproject_path = os.path.join(project_path, "pyproject.toml")
    with open(pyproject_path, "r") as pyproject_file:
        assert "entry-points" in pyproject_file.read()


def test_bake_with_console_script_cli(cookies):
    result = cookies.bake()
    project_path, project_slug, project_dir = project_info(result)
    module_path = os.path.join(project_dir, "cli.py")
    module_name = ".".join([project_slug, "cli"])
    if sys.version_info >= (3, 5):
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
    elif sys.version_info >= (3, 3):
        file_loader = importlib.machinery.SourceFileLoader
        cli = file_loader(module_name, module_path).load_module()
    else:
        cli = imp.load_source(module_name, module_path)
    runner = CliRunner()
    noarg_result = runner.invoke(cli.main)
    assert noarg_result.exit_code == 0
    noarg_output = " ".join(["Replace this message by putting your code into", project_slug])
    assert noarg_output in noarg_result.output
    help_result = runner.invoke(cli.main, ["--help"])
    assert help_result.exit_code == 0
    assert "Show this message" in help_result.output
