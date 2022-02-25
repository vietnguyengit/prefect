"""
Command line interface for working with work queues.
"""
from typing import List
from uuid import UUID

import anyio
import pendulum
import typer
from rich.pretty import Pretty
from rich.table import Table

from prefect.cli.base import (
    PrefectTyper,
    app,
    console,
    exit_with_error,
    exit_with_success,
)
from prefect.client import get_client

work_app = PrefectTyper(name="work-queue", help="Commands for work queue CRUD.")
app.add_typer(work_app)


@work_app.command()
async def create(
    name: str = typer.Argument(..., help="The unique name to assign this work queue"),
    tags: List[str] = typer.Option(
        None, "-t", "--tag", help="One or more optional tags"
    ),
    deployment_ids: List[UUID] = typer.Option(
        None, "-d", "--deployment", help="One or more optional deployment IDs"
    ),
    flow_runner_types: List[str] = typer.Option(
        None, "-fr", "--flow-runner", help="One or more optional flow runner types"
    ),
):
    """
    Create a work queue.
    """
    async with get_client() as client:
        result = await client.create_work_queue(
            name=name,
            tags=tags or None,
            deployment_ids=deployment_ids or None,
            flow_runner_types=flow_runner_types or None,
        )

    console.print(Pretty(result))


@work_app.command()
async def set_concurrency_limit(
    id: UUID = typer.Argument(..., help="The id of the work queue"),
    limit: int = typer.Argument(..., help="The concurrency limit to set on the queue."),
):
    """
    Set a concurrency limit on a work queue.
    """
    async with get_client() as client:
        result = await client.update_work_queue(
            id=id,
            concurrency_limit=limit,
        )

    if result:
        exit_with_success(f"Concurrency limit of {limit} set on work queue {id}")
    else:
        exit_with_error(f"No work queue found with id {id}")


@work_app.command()
async def clear_concurrency_limit(
    id: UUID = typer.Argument(..., help="The id of the work queue to clear"),
):
    """
    Clear any concurrency limits from a work queue.
    """
    async with get_client() as client:
        result = await client.update_work_queue(
            id=id,
            concurrency_limit=None,
        )

    if result:
        exit_with_success(f"Concurrency limits removed on work queue {id}")
    else:
        exit_with_error(f"No work queue found with id {id}")


@work_app.command()
async def pause(
    id: UUID = typer.Argument(..., help="The ID of the work queue to pause."),
):
    """
    Pause a work queue.
    """
    async with get_client() as client:
        result = await client.update_work_queue(
            id=id,
            is_paused=True,
        )

    if result:
        exit_with_success(f"Paused work queue {id}")
    else:
        exit_with_error(f"No work queue found with id {id}")


@work_app.command()
async def unpause(
    id: UUID = typer.Argument(..., help="The ID of the work queue to pause."),
):
    """
    Unpause a work queue.
    """
    async with get_client() as client:
        result = await client.update_work_queue(
            id=id,
            is_paused=False,
        )

    if result:
        exit_with_success(f"Unpaused work queue {id}")
    else:
        exit_with_error(f"No work queue found with id {id}")


@work_app.command()
async def inspect(id: UUID):
    """
    Inspect a work queue by ID.
    """
    async with get_client() as client:
        result = await client.read_work_queue(id=id)

    console.print(Pretty(result))


@work_app.command()
async def ls():
    """
    View all work queues.
    """
    table = Table(
        title="Work Queues", caption="(**) denotes a paused queue", caption_style="red"
    )
    table.add_column("ID", justify="right", style="cyan", no_wrap=True)
    table.add_column("Name", style="green", no_wrap=True)
    table.add_column("Concurrency Limit", style="blue", no_wrap=True)
    table.add_column("Filter", style="magenta", no_wrap=True)

    async with get_client() as client:
        queues = await client.read_work_queues()

    sort_by_created_key = lambda q: pendulum.now("utc") - q.created

    for queue in sorted(queues, key=sort_by_created_key):
        table.add_row(
            str(queue.id),
            f"{queue.name} [red](**)" if queue.is_paused else queue.name,
            f"[red]{queue.concurrency_limit}"
            if queue.concurrency_limit
            else "[blue]None",
            queue.filter.json(),
        )

    console.print(table)


@work_app.command()
async def preview(
    id: UUID = typer.Argument(..., help="The id of the work queue"),
    hours: int = typer.Option(
        None,
        "-h",
        "--hours",
        help="The number of hours to look ahead; defaults to 1 hour",
    ),
):
    """
    Preview a work queue.
    """
    table = Table(caption="(**) denotes a late run", caption_style="red")
    table.add_column(
        "Scheduled Start Time", justify="left", style="yellow", no_wrap=True
    )
    table.add_column("Run ID", justify="left", style="cyan", no_wrap=True)
    table.add_column("Name", style="green", no_wrap=True)
    table.add_column("Deployment ID", style="blue", no_wrap=True)

    window = pendulum.now("utc").add(hours=hours or 1)
    async with get_client() as client:
        runs = await client.get_runs_in_work_queue(
            id, limit=10, scheduled_before=window
        )

    now = pendulum.now("utc")
    sort_by_created_key = lambda r: now - r.created

    for run in sorted(runs, key=sort_by_created_key):
        table.add_row(
            f"{run.expected_start_time} [red](**)"
            if run.expected_start_time < now
            else f"{run.expected_start_time}",
            str(run.id),
            run.name,
            str(run.deployment_id),
        )

    if runs:
        console.print(table)
    else:
        console.print(
            "No runs found - try increasing how far into the future you preview with the --hours flag",
            style="yellow",
        )


@work_app.command()
async def delete(id: UUID):
    """
    Delete a work queue by ID.
    """
    async with get_client() as client:
        result = await client.delete_work_queue_by_id(id=id)

    if result:
        exit_with_success(f"Deleted work queue {id}")
    else:
        exit_with_error(f"No work queue found with id {id}")