"""Commit command - auto-commit and push subfolders with recently updated README.md."""

import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import click


def get_readme_mtime(folder_path: Path) -> datetime | None:
    """Get the modification time of README.md in the given folder."""
    readme_path = folder_path / "README.md"
    if readme_path.exists():
        return datetime.fromtimestamp(readme_path.stat().st_mtime)
    return None


def is_git_repo(folder_path: Path) -> bool:
    """Check if the folder is a git repository."""
    return (folder_path / ".git").is_dir()


def has_changes(folder_path: Path) -> bool:
    """Check if the git repo has uncommitted changes."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=folder_path,
        capture_output=True,
        text=True
    )
    return bool(result.stdout.strip())


def git_commit_and_push(folder_path: Path, dry_run: bool = False) -> tuple[bool, str]:
    """
    Commit all changes and push to remote.

    Returns (success, message).
    """
    folder_name = folder_path.name

    if dry_run:
        return True, f"[DRY RUN] Would commit and push changes in {folder_name}"

    try:
        # Stage all changes
        subprocess.run(
            ["git", "add", "-A"],
            cwd=folder_path,
            check=True,
            capture_output=True
        )

        # Create commit with timestamp
        commit_msg = f"Auto-commit: {folder_name} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=folder_path,
            check=True,
            capture_output=True
        )

        # Push to remote
        result = subprocess.run(
            ["git", "push"],
            cwd=folder_path,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            # Try to push with upstream set
            result = subprocess.run(
                ["git", "push", "-u", "origin", "HEAD"],
                cwd=folder_path,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                return False, f"Push failed for {folder_name}: {result.stderr}"

        return True, f"Successfully committed and pushed changes in {folder_name}"

    except subprocess.CalledProcessError as e:
        return False, f"Git operation failed for {folder_name}: {e.stderr.decode() if e.stderr else str(e)}"


@click.command()
@click.option(
    '--days',
    default=30,
    help='Number of days to look back for README.md modifications (default: 30)',
    type=int
)
@click.option(
    '--dry-run',
    is_flag=True,
    help='Preview changes without actually committing or pushing'
)
@click.option(
    '--path',
    default='.',
    help='Base path to scan for subfolders (default: current directory)',
    type=click.Path(exists=True, file_okay=False, dir_okay=True)
)
def commit(days, dry_run, path):
    """
    Commit and push subfolders with recently updated README.md files.

    Scans all immediate subfolders of the current directory (or specified path)
    for git repositories that have a README.md file modified within the last N days.
    For each matching folder with uncommitted changes, it commits all files and
    pushes to the remote repository.

    Example:
        nc commit                    # Commit folders with README.md updated in last 30 days
        nc commit --days 7           # Only last 7 days
        nc commit --dry-run          # Preview without making changes
        nc commit --path ~/projects  # Scan a specific directory
    """
    base_path = Path(path).resolve()
    cutoff_date = datetime.now() - timedelta(days=days)

    click.echo(f"Scanning subfolders in: {base_path}")
    click.echo(f"Looking for README.md files modified since: {cutoff_date.strftime('%Y-%m-%d')}")

    if dry_run:
        click.echo(click.style("[DRY RUN MODE]", fg="yellow", bold=True))

    click.echo("")

    processed = 0
    committed = 0
    skipped = 0
    errors = 0

    # Iterate through immediate subfolders
    for item in sorted(base_path.iterdir()):
        if not item.is_dir():
            continue

        # Skip hidden folders
        if item.name.startswith('.'):
            continue

        # Check if it's a git repo
        if not is_git_repo(item):
            continue

        processed += 1

        # Check README.md modification time
        readme_mtime = get_readme_mtime(item)
        if readme_mtime is None:
            click.echo(f"  {item.name}: No README.md found, skipping")
            skipped += 1
            continue

        if readme_mtime < cutoff_date:
            click.echo(f"  {item.name}: README.md not recently updated ({readme_mtime.strftime('%Y-%m-%d')}), skipping")
            skipped += 1
            continue

        # Check for uncommitted changes
        if not has_changes(item):
            click.echo(f"  {item.name}: No uncommitted changes, skipping")
            skipped += 1
            continue

        click.echo(f"  {item.name}: README.md updated on {readme_mtime.strftime('%Y-%m-%d')}, has changes")

        # Commit and push
        success, message = git_commit_and_push(item, dry_run=dry_run)
        if success:
            click.echo(click.style(f"    ✓ {message}", fg="green"))
            committed += 1
        else:
            click.echo(click.style(f"    ✗ {message}", fg="red"))
            errors += 1

    # Summary
    click.echo("")
    click.echo("Summary:")
    click.echo(f"  Folders scanned: {processed}")
    click.echo(f"  Committed/pushed: {committed}")
    click.echo(f"  Skipped: {skipped}")
    if errors:
        click.echo(click.style(f"  Errors: {errors}", fg="red"))
