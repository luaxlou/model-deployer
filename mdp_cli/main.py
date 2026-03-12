from __future__ import annotations

from pathlib import Path
import json

import typer
from rich.console import Console
from rich.table import Table

from mdp_cli import codes
from mdp_cli.blueprint import load_blueprint
from mdp_cli.pipeline import build as run_build
from mdp_cli.pipeline import deploy as run_deploy
from mdp_cli.pipeline import lint as run_lint
from mdp_cli.pipeline import rollout as run_rollout
from mdp_cli.pipeline import verify as run_verify
from mdp_cli.providers import get_provider

app = typer.Typer(help="Stateless model deployment CLI")
console = Console()


def _echo_json(data: dict):
    console.print_json(json.dumps(data, ensure_ascii=False))


@app.command()
def lint(
    d: Path = typer.Option(..., "-d", "--dir", help="Blueprint directory"),
):
    ok, errs = run_lint(d)
    if not ok:
        for err in errs:
            console.print(f"[red]- {err}[/red]")
        raise typer.Exit(code=codes.VALIDATION_ERROR)
    console.print("[green]lint passed[/green]")


@app.command()
def plan(
    d: Path = typer.Option(..., "-d", "--dir", help="Blueprint directory"),
    out: Path | None = typer.Option(None, "--out", help="Output plan json file"),
):
    bp = load_blueprint(d)
    data = {
        "name": bp.name,
        "provider": bp.provider,
        "pipeline": ["build", "deploy", "verify"],
        "defaults": {
            "follow": True,
            "env": "prod",
        },
    }
    if out:
        out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        console.print(f"[green]plan written:[/green] {out}")
    else:
        _echo_json(data)


@app.command()
def build(
    d: Path = typer.Option(..., "-d", "--dir", help="Blueprint directory"),
):
    image = run_build(d)
    _echo_json({"image": image})


@app.command()
def rollout(
    d: Path = typer.Option(..., "-d", "--dir", help="Blueprint directory"),
    image: str = typer.Option(..., "--image", help="Image ref to deploy"),
    env: str = typer.Option("prod", "--env"),
    follow: bool = typer.Option(True, "--follow/--no-follow"),
):
    _ = follow
    res = run_rollout(d, image=image, env=env)
    _echo_json(
        {
            "status": res.status,
            "endpoint": res.endpoint,
            "container_name": res.container_name,
        }
    )


@app.command()
def verify(
    d: Path = typer.Option(..., "-d", "--dir", help="Blueprint directory"),
    timeout_sec: int | None = typer.Option(None, "--timeout-sec"),
    interval_sec: int | None = typer.Option(None, "--interval-sec"),
):
    ok, msg = run_verify(d, timeout_sec=timeout_sec, interval_sec=interval_sec)
    if not ok:
        console.print(f"[red]{msg}[/red]")
        raise typer.Exit(code=codes.VERIFY_ERROR)
    console.print(f"[green]{msg}[/green]")


@app.command()
def deploy(
    d: Path = typer.Option(..., "-d", "--dir", help="Blueprint directory"),
    env: str = typer.Option("prod", "--env"),
    follow: bool = typer.Option(True, "--follow/--no-follow"),
    build_only: bool = typer.Option(False, "--build-only", help="Only run lint + build"),
):
    _ = follow
    result = run_deploy(d, env=env, build_only=build_only)
    _echo_json(result)

    if not result.get("ok", False):
        stage = result.get("stage")
        if stage == "verify":
            raise typer.Exit(code=codes.VERIFY_ERROR)
        if stage == "build":
            raise typer.Exit(code=codes.BUILD_ERROR)
        raise typer.Exit(code=codes.DEPLOY_ERROR)


@app.command()
def status(
    d: Path = typer.Option(..., "-d", "--dir", help="Blueprint directory"),
):
    bp = load_blueprint(d)
    p = get_provider(bp.provider)
    _echo_json(p.status(bp))


@app.command()
def logs(
    d: Path = typer.Option(..., "-d", "--dir", help="Blueprint directory"),
    tail: int = typer.Option(200, "--tail"),
):
    bp = load_blueprint(d)
    p = get_provider(bp.provider)
    for line in p.logs(bp, tail=tail):
        console.print(line)


@app.command()
def cost(
    d: Path = typer.Option(..., "-d", "--dir", help="Blueprint directory"),
    group_by: str = typer.Option("deployment", "--group-by"),
):
    bp = load_blueprint(d)
    p = get_provider(bp.provider)
    data = p.cost(bp, group_by=group_by)

    table = Table(title="Cost")
    table.add_column("deployment")
    table.add_column("group_by")
    table.add_column("total_usd")
    table.add_row(str(data["deployment"]), str(data["group_by"]), str(data["total_usd"]))
    console.print(table)


def run() -> None:
    app()


if __name__ == "__main__":
    run()
