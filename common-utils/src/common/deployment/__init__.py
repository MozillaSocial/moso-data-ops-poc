from pathlib import Path
from subprocess import PIPE, STDOUT, Popen

import typer
import yaml
from rich import print

app = typer.Typer()


def run_command(command: str) -> str:
    """Helper function to execute shell commands.
    Provides stream logging of stdout and returns the last line
    for return values from scripts.

    Args:
        command (str): Shell command to run.

    Raises:
        Exception: Throws when exit code is not zero.

    Returns:
        str: Last line from stdout.
    """
    line = "Running Shell Command..."
    with Popen(
        command, stdout=PIPE, stderr=STDOUT, shell=True, executable="/bin/bash"
    ) as sub_process:
        for raw_line in iter(sub_process.stdout.readline, b""):  # type: ignore
            line = raw_line.decode("utf-8").rstrip()
            print(line)

        sub_process.wait()
        if sub_process.returncode:
            msg = "Command failed with exit code {}".format(
                sub_process.returncode,
            )
            print(msg)
            raise Exception(f"Shell Command Failed with last line: {line}!")
    return line


def enrich_yaml(project_path):
    config_file_path = "prefect.yaml"
    with open(config_file_path, "r") as yaml_file:
        yaml_data = yaml.full_load(yaml_file)

    pull_step = {
        "prefect.deployments.steps.run_shell_script": {
            "id": "pull-subfolder",
            "script": "msdo pull-subproject {{ $MOZILLA_PREFECT_GIT_REPO }} {{ $MOZILLA_PREFECT_GIT_BRANCH }} {{ $MOZILLA_PREFECT_GIT_SUBFOLDER }} /opt/prefect",  # noqa: E501
            "stream_output": False,
        }
    }
    yaml_data["pull"].insert(0, pull_step)
    with open(config_file_path, "w") as yaml_file:
        yaml.dump_all(yaml_data, yaml_file, sort_keys=False)


@app.command()
def prefect_init(project_name: str):
    run_command("prefect init --recipe local")
    enrich_yaml("prefect.yaml")


@app.command()
def pull_subproject(
    repo: str, branch: str, subproject_folder: str, working_directory: str
):
    command = f"""mkdir -p {working_directory} && \
    pushd {working_directory} && \
    git init && \
    git remote add -f origin {repo} && \
    git config core.sparseCheckout true && \
    echo '{subproject_folder}' >> .git/info/sparse-checkout && \
    git pull origin {branch}
    popd"""
    run_command(command)


def main():
    app()


if __name__ == "__main__":
    main()
