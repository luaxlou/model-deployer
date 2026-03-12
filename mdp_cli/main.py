from __future__ import annotations

from pathlib import Path
import json

import typer
from rich.console import Console
from rich.table import Table

from mdp_cli import codes
from mdp_cli.blueprint import load_blueprint
from mdp_cli.pipeline import build as run_build
from mdp_cli.pipeline import lint as run_lint
from mdp_cli.pipeline import deploy as run_deploy
from mdp_cli.pipeline import push as run_push
from mdp_cli.pipeline import release as run_release
from mdp_cli.pipeline import verify as run_verify
from mdp_cli.providers import get_provider

app = typer.Typer(help="Stateless model deployment CLI")
console = Console()
progress_console = Console(stderr=True)


def _echo_json(data: dict):
    console.print_json(json.dumps(data, ensure_ascii=False))


def _resolve_provider(bp, provider: str | None) -> str:
    configured = bp.deploy.configured_providers
    if not configured:
        raise typer.BadParameter("no deploy providers configured in blueprint")

    if provider:
        if provider not in configured:
            raise typer.BadParameter(
                f"provider '{provider}' is not configured; available: {', '.join(configured)}"
            )
        return provider

    if bp.deploy.default:
        return bp.deploy.default

    if len(configured) == 1:
        return configured[0]

    choice = typer.prompt(
        f"Select deploy provider ({', '.join(configured)})",
        default=configured[0],
    ).strip()
    if choice not in configured:
        raise typer.BadParameter(f"invalid provider '{choice}'; available: {', '.join(configured)}")
    return choice


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
        "default_provider": bp.deploy.default,
        "providers": bp.deploy.configured_providers,
        "pipeline": ["build", "push", "deploy", "verify"],
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
    provider: str | None = typer.Option(None, "--provider"),
):
    bp = load_blueprint(d)
    resolved_provider = _resolve_provider(bp, provider)
    progress_console.print(f"[cyan]provider:[/cyan] {resolved_provider}")
    progress_console.print("[cyan]stage:[/cyan] build (start)")
    image = run_build(d, provider=resolved_provider)
    progress_console.print("[green]stage:[/green] build (done)")
    _echo_json({"ok": True, "stage": "build", "image": image})


@app.command()
def push(
    d: Path = typer.Option(..., "-d", "--dir", help="Blueprint directory"),
    image: str | None = typer.Option(None, "--image", help="Image ref to push; defaults to last build image"),
    provider: str | None = typer.Option(None, "--provider"),
):
    bp = load_blueprint(d)
    resolved_provider = _resolve_provider(bp, provider)
    progress_console.print(f"[cyan]provider:[/cyan] {resolved_provider}")
    progress_console.print("[cyan]stage:[/cyan] push (start)")
    pushed = run_push(d, provider=resolved_provider, image=image)
    progress_console.print("[green]stage:[/green] push (done)")
    _echo_json({"ok": True, "stage": "push", "image": pushed})


@app.command()
def deploy(
    d: Path = typer.Option(..., "-d", "--dir", help="Blueprint directory"),
    image: str | None = typer.Option(None, "--image", help="Image ref to deploy; defaults to last build image"),
    provider: str | None = typer.Option(None, "--provider"),
    env: str = typer.Option("prod", "--env"),
    follow: bool = typer.Option(True, "--follow/--no-follow"),
):
    _ = follow
    bp = load_blueprint(d)
    resolved_provider = _resolve_provider(bp, provider)
    progress_console.print(f"[cyan]provider:[/cyan] {resolved_provider}")
    progress_console.print("[cyan]stage:[/cyan] deploy (start)")
    res = run_deploy(d, provider=resolved_provider, image=image, env=env)
    progress_console.print("[green]stage:[/green] deploy (done)")
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
    provider: str | None = typer.Option(None, "--provider"),
    timeout_sec: int | None = typer.Option(None, "--timeout-sec"),
    interval_sec: int | None = typer.Option(None, "--interval-sec"),
):
    bp = load_blueprint(d)
    resolved_provider = _resolve_provider(bp, provider)
    progress_console.print(f"[cyan]provider:[/cyan] {resolved_provider}")
    progress_console.print("[cyan]stage:[/cyan] verify (start)")
    ok, msg = run_verify(
        d,
        provider=resolved_provider,
        timeout_sec=timeout_sec,
        interval_sec=interval_sec,
    )
    if not ok:
        console.print(f"[red]{msg}[/red]")
        progress_console.print("[red]stage:[/red] verify (failed)")
        raise typer.Exit(code=codes.VERIFY_ERROR)
    console.print(f"[green]{msg}[/green]")
    progress_console.print("[green]stage:[/green] verify (done)")


@app.command()
def release(
    d: Path = typer.Option(..., "-d", "--dir", help="Blueprint directory"),
    provider: str | None = typer.Option(None, "--provider"),
    env: str = typer.Option("prod", "--env"),
    follow: bool = typer.Option(True, "--follow/--no-follow"),
):
    _ = follow
    bp = load_blueprint(d)
    resolved_provider = _resolve_provider(bp, provider)
    progress_console.print(f"[cyan]provider:[/cyan] {resolved_provider}")
    progress_console.print("[cyan]pipeline:[/cyan] build -> push -> deploy -> verify")
    result = run_release(d, provider=resolved_provider, env=env)
    _echo_json(result)

    if not result.get("ok", False):
        stage = result.get("stage")
        progress_console.print(f"[red]stage:[/red] {stage} (failed)")
        if stage == "verify":
            raise typer.Exit(code=codes.VERIFY_ERROR)
        if stage == "build":
            raise typer.Exit(code=codes.BUILD_ERROR)
        if stage == "push":
            raise typer.Exit(code=codes.BUILD_ERROR)
        raise typer.Exit(code=codes.DEPLOY_ERROR)
    progress_console.print(f"[green]stage:[/green] {result.get('stage', 'unknown')} (done)")


@app.command()
def status(
    d: Path = typer.Option(..., "-d", "--dir", help="Blueprint directory"),
    provider: str | None = typer.Option(None, "--provider"),
):
    bp = load_blueprint(d)
    p = get_provider(_resolve_provider(bp, provider))
    _echo_json(p.status(bp))


@app.command()
def logs(
    d: Path = typer.Option(..., "-d", "--dir", help="Blueprint directory"),
    provider: str | None = typer.Option(None, "--provider"),
    tail: int = typer.Option(200, "--tail"),
):
    bp = load_blueprint(d)
    p = get_provider(_resolve_provider(bp, provider))
    for line in p.logs(bp, tail=tail):
        console.print(line)


@app.command()
def cost(
    d: Path = typer.Option(..., "-d", "--dir", help="Blueprint directory"),
    provider: str | None = typer.Option(None, "--provider"),
    group_by: str = typer.Option("deployment", "--group-by"),
):
    bp = load_blueprint(d)
    p = get_provider(_resolve_provider(bp, provider))
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
