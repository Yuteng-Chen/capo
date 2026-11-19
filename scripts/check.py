"""Check the text-only release and its one synthetic example without dependencies."""

import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SKILL = Path("skills/capo")
EXAMPLE = Path("examples/synthetic-run.json")
BINDING_FIELDS = ("task_id", "requirement_version", "context_revision", "assignment_revision")
PRIVACY_PATTERNS = {
    "absolute user path": re.compile(
        r"""(?i)(?<![\w./:-])(?:file://)?(?:/(?:users|home|var/home|root|(?:private/)?var/folders)/"""
        r"""|[a-z]:[\\/]+(?:users|documents and settings)[\\/]+)[^\s/"'<>`)\\]+"""
    ),
    "possible credential": re.compile(
        r"\b(?:gh[pousr]_[A-Za-z0-9]{24,}|github_pat_[A-Za-z0-9_]{30,}"
        r"|sk-[A-Za-z0-9_-]{20,}|xox[baprs]-[A-Za-z0-9-]{16,}|AKIA[A-Z0-9]{16}"
        r"|eyJ[\w-]{8,}\.eyJ[\w-]{8,}\.[\w-]{8,})\b|-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----"
    ),
}
DESTINATION = re.compile(r"(?:\]\(\s*|^ {0,3}\[[^\]\n]+\]:\s*)(?:<([^>\n]+)>|([^\s)]+))")


class CheckError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise CheckError(message)


def resolved_inside(path, label, *, strict=True):
    try:
        target = path.resolve(strict=strict)
    except (OSError, RuntimeError):
        raise CheckError(f"{label}: unreadable or dangling path") from None
    require(target.is_relative_to(ROOT), f"{label}: path escapes the release directory")
    return target


def check_privacy(text, label):
    for issue, pattern in PRIVACY_PATTERNS.items():
        match = pattern.search(text)
        if match:
            line = text.count("\n", 0, match.start()) + 1
            raise CheckError(f"{label}:{line}: {issue}")


def load_release_files():
    files = {}

    def walk_error(_error):
        raise CheckError("Unable to read a release directory")

    for directory, subdirs, names in os.walk(ROOT, onerror=walk_error):
        subdirs[:] = sorted(name for name in subdirs if name != ".git")
        for name in [*subdirs, *sorted(set(names) - {".git"})]:
            path = Path(directory, name)
            relative = path.relative_to(ROOT)
            check_privacy("/" + relative.as_posix(), "release path")
            if path.is_symlink():
                raise CheckError(f"{relative}: symlinks are not part of this text-only release")
            if name in subdirs:
                continue
            require(path.is_file(), f"{relative}: expected a regular file")
            try:
                files[relative] = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                raise CheckError(f"{relative}: expected readable UTF-8 text") from None
            check_privacy(files[relative], relative)
    return files


def check_markdown_links(files):
    for path, content in files.items():
        if path.suffix.lower() != ".md":
            continue
        fence = None
        for line_number, line in enumerate(content.splitlines(), 1):
            marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
            if marker:
                run, rest = marker.groups()
                if not fence:
                    fence = run
                elif run.startswith(fence) and not rest.strip():
                    fence = None
                continue
            if fence:
                continue
            line = re.sub(r"(`+)[^\n]*?\1", "", line)
            for link in DESTINATION.finditer(line):
                destination = urlsplit(link.group(1) or link.group(2))
                if destination.scheme or destination.netloc or not destination.path:
                    continue
                label = f"{path}:{line_number}"
                target = resolved_inside(ROOT / path.parent / unquote(destination.path), label, strict=False)
                require(target.exists(), f"{label}: missing local Markdown link target")


def check_metadata(files):
    for required in (
        "README.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "CHANGELOG.md", "VERSION",
        "docs/validation.md", "examples/synthetic-run.json", "scripts/check.py",
        "tests/isolation-check.mjs", "tests/scenarios.md", ".github/workflows/check.yml",
    ):
        require(files.get(Path(required), "").strip(), f"{required}: missing or empty release file")
    version = files[Path("VERSION")].strip()
    require(re.fullmatch(r"(?:0|[1-9]\d*)(?:\.(?:0|[1-9]\d*)){2}", version), "VERSION: expected MAJOR.MINOR.PATCH")
    skill_file = SKILL / "SKILL.md"
    frontmatter = re.match(r"\A---[ \t]*\n(.*?)\n---[ \t]*\n", files[skill_file], re.DOTALL)
    require(frontmatter, f"{skill_file}: missing delimited YAML front matter")
    names = re.findall(r"(?m)^name:[ \t]*(.*)$", frontmatter[1])
    descriptions = re.findall(r"(?m)^description:[ \t]*(.+)$", frontmatter[1])
    require(len(names) == 1 and names[0].strip().strip("'\"") == SKILL.name, f"{skill_file}: invalid skill name")
    require(len(descriptions) == 1 and descriptions[0].strip(), f"{skill_file}: missing skill description")
    for required in (
        "agents/openai.yaml",
        "references/coordination-protocol.md",
        "references/record-format.md",
        "references/runtime-policy.md",
    ):
        require(files.get(SKILL / required, "").strip(), f"{SKILL / required}: missing or empty")
    return version


def digest(artifact):
    canonical = json.dumps(artifact, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("ascii")).hexdigest()


def check_example(content, version):
    run = json.loads(content)
    require(run["synthetic"] is True and run["release_version"] == version, "example: synthetic label or release version mismatch")
    first, current = run["revisions"]
    require(type(first["assignment_revision"]) is int and first["assignment_revision"] > 0, "example: invalid assignment revision")
    previous = {}
    evidence_ids = set()
    for index, revision in enumerate((first, current), 1):
        for key in ("task_id", "assignment_revision", "worker_alias"):
            require(revision[key] == first[key], f"example: {key} changed during the same assignment")
        for key in ("requirement_version", "context_revision"):
            require(type(revision[key]) is int and revision[key] == index, f"example: invalid {key} sequence")

        criteria = revision["criteria"]
        events = revision["events"]
        opening = ["assigned"] if index == 1 else ["requirement_updated", "message_sent", "message_ack"]
        expected = opening + ["worker_report"] + ["acceptance"] * len(criteria)
        require([event["event"] for event in events] == expected, "example: invalid event order")
        report = events[len(opening)]
        require(report["worker_alias"] == revision["worker_alias"] and report["status"] == "ready", "example: invalid Worker report")
        require(report["artifacts"].keys() == criteria.keys() and criteria, "example: missing criterion or artifact mapping")

        if index == 2:
            updated, sent, ack = events[:3]
            require(sent["worker_alias"] == ack["worker_alias"] == revision["worker_alias"], "example: update recipient mismatch")
            require(sent["message_id"] and sent["message_id"] == ack["message_id"], "example: acknowledgement must reference the sent update")
            require(criteria.keys() == first["criteria"].keys(), "example: expected the same criterion IDs")
            changed = {key for key in criteria if criteria[key] != first["criteria"][key]}
            require(changed and set(updated["changed_criteria"]) == changed, "example: changed criterion list mismatch")
            require(set(updated["invalidated_evidence"]) == {previous[key]["evidence_id"] for key in changed}, "example: stale evidence was not invalidated")

        reviewed = {}
        for item in events[len(opening) + 1:]:
            criterion = item["criterion_id"]
            require(criterion in criteria and criterion not in reviewed, "example: invalid or duplicate criterion evidence")
            artifact_id = report["artifacts"][criterion]
            for field in BINDING_FIELDS:
                require(item[field] == revision[field] and type(item[field]) is type(revision[field]), f"example: stale acceptance binding for {field}")
            require(item["evidence_id"] and item["evidence_id"] not in evidence_ids, "example: duplicate or empty evidence ID")
            require(item["artifact_digest"] == digest(run["artifacts"][artifact_id]), "example: artifact digest mismatch")
            require(item["evidence_location"] == f"#/artifacts/{artifact_id}", "example: invalid evidence location")
            require(item["reviewer_alias"] and item["reviewer_alias"] != revision["worker_alias"], "example: expected independent reviewer")
            require(item["result"] == "passed" and item["method"].strip() and item["observation"].strip(), "example: incomplete review")
            if "carried_from" in item:
                old = previous.get(criterion)
                require(
                    old and item["carried_from"] == old["evidence_id"]
                    and criteria[criterion] == first["criteria"][criterion]
                    and item["artifact_digest"] == old["artifact_digest"]
                    and item["carry_reason"].strip(),
                    "example: carried evidence must bind the same criterion and artifact digest",
                )
            evidence_ids.add(item["evidence_id"])
            reviewed[criterion] = item
        previous = reviewed
    require(any("carried_from" in item for item in previous.values()), "example: missing explicit carry-forward")


def main():
    try:
        files = load_release_files()
        version = check_metadata(files)
        check_markdown_links(files)
        check_example(files[EXAMPLE], version)
    except CheckError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as error:
        print(f"FAIL: {EXAMPLE}:{error.lineno}: invalid JSON", file=sys.stderr)
        return 1
    except (AttributeError, KeyError, TypeError, ValueError):
        print("FAIL: missing required release file, malformed link, or malformed synthetic example", file=sys.stderr)
        return 1
    print(f"PASS: {len(files)} release files, skill metadata, local links, common privacy patterns, and synthetic evidence bindings.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
