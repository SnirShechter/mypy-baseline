from __future__ import annotations

from .._error import Error
from ._base import Command


class Sync(Command):
    """Generate baseline with all existing errors.
    """

    def run(self) -> int:
        try:
            baseline_text = self.config.baseline_path.read_text(encoding='utf8')
        except FileNotFoundError:
            baseline_text = ''
        old_baseline = baseline_text.splitlines()

        new_baseline: list[str] = []
        for line in self.stdin:
            error = Error.new(line)
            if error is None:
                self.print(line, end='')
                continue
            if self.config.is_ignored(error.message):
                continue
            if self.config.is_ignored_category(error.category):
                continue
            clean_line = error.get_clean_line(self.config)
            new_baseline.append(clean_line)

        if self.config.sort_baseline:
            new_baseline.sort()

        synced = False
        if old_baseline:
            synced = self._stable_sync(old_baseline, new_baseline)
        if not synced:
            self._write_baseline(new_baseline)
        return 0

    def _stable_sync(self, old_bline: list[str], new_bline: list[str]) -> bool:
        """Try to cleanly update the old baseline instead of rewriting it.

        We do that to avoid lines jumping around that happens because of not ordered
        output from mypy.

        Currently, we can do a stable sync only when there are no new lines added.
        It's hard to insert new lines in the correct positions, and adding them
        at the end of the file will cause merge conflicts.
        Sorting lines solves the issue, so we don't use stable sync when the output
        is sorted.
        However, sorting is not enabled by default because I want to keep backward
        compatibility.
        """
        if not self.config.sort_baseline:
            return False
        old_set = set(old_bline)
        new_set = set(new_bline)
        removed = old_set - new_set
        added = new_set - old_set
        if added:
            return False
        result = [line for line in old_bline if line not in removed]
        self._write_baseline(result)
        return True

    def _write_baseline(self, baseline: list[str]) -> None:
        """Serialize baseline and write it into the file.
        """
        serialized = '\n'.join(baseline) + '\n'
        self.config.baseline_path.write_text(serialized, encoding='utf8')
