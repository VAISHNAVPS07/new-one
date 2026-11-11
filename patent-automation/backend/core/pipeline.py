"""Stage runner with checkpointing. Later phases register more stages here."""
import logging
from dataclasses import dataclass, field
from typing import Callable

from backend.core.audit import append_audit
from backend.core.config import Settings
from backend.core.jobs import JobPaths, JobStore

log = logging.getLogger(__name__)


@dataclass
class JobContext:
    store: JobStore
    settings: Settings
    paths: JobPaths
    force: bool = False
    actor: str = "system"


@dataclass
class StageRunner:
    stage: str
    fn: Callable[[JobContext], dict | None]
    outputs: list[str] = field(default_factory=list)  # paths relative to job root, for resume checks


def _already_done(ctx: JobContext, runner: StageRunner) -> bool:
    if ctx.force:
        return False
    status = ctx.store.read_stages(ctx.paths).get(runner.stage, {}).get("status")
    return status == "done" and all((ctx.paths.root / o).exists() for o in runner.outputs)


def run_pipeline(ctx: JobContext, runners: list[StageRunner]) -> bool:
    """Run stages in order; skip completed ones (resume); stop at first failure."""
    for runner in runners:
        if _already_done(ctx, runner):
            log.info("%s: %s already done, skipping", ctx.paths.job_id, runner.stage)
            continue
        ctx.store.set_stage(ctx.paths, runner.stage, "running")
        append_audit(ctx.paths.root, "stage_started", ctx.actor, stage=runner.stage)
        try:
            extra = runner.fn(ctx) or {}
        except Exception as exc:
            log.exception("%s: stage %s failed", ctx.paths.job_id, runner.stage)
            ctx.store.set_stage(ctx.paths, runner.stage, "failed", error=f"{type(exc).__name__}: {exc}")
            append_audit(ctx.paths.root, "stage_failed", ctx.actor, stage=runner.stage, error=str(exc))
            return False
        ctx.store.set_stage(ctx.paths, runner.stage, "done", **extra)
        append_audit(ctx.paths.root, "stage_done", ctx.actor, stage=runner.stage)
    return True
