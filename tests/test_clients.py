import json
import os
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ.get("GUIDE_SOURCE", ROOT))
STATE = {
    "session_id": "sess-test",
    "environment_id": "env-test",
    "remote_url": "wss://executor.example",
}


@pytest.fixture
def api():
    data = {
        "requests": [],
        "case": "ok",
        "submitted": threading.Event(),
        "stream_open": threading.Event(),
        "deletes": 0,
    }

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def record(self):
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n)) if n else None
            data["requests"].append((self.command, self.path, dict(self.headers), body))
            return body

        def reply(self, status, obj):
            body = json.dumps(obj).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            body = self.record()
            if self.path.endswith("/events"):
                assert data["stream_open"].is_set()
                data["submitted"].set()
                self.reply(
                    400 if data["case"] == "submit_error" else 202,
                    {}
                    if data["case"] != "submit_error"
                    else {"error": {"message": "test submission error"}},
                )
            else:
                assert body["environment"] == {
                    "type": "self_hosted",
                    "workspace_directory": "/workspace",
                }
                self.reply(
                    200,
                    {
                        "id": "sess-test",
                        "environment": {
                            "type": "self_hosted",
                            "id": "env-test",
                            "remote_url": "wss://executor.example",
                        },
                    },
                )

        def do_GET(self):
            self.record()
            events = [{"type": "agent.session.created", "session": {"id": "sess-test"}}]

            def turn(status, subagent=None):
                return {
                    "type": "agent.session.turn." + status,
                    "session_id": "sess-test",
                    "turn": {"id": "turn-test", "subagent_id": subagent},
                }

            events.append(turn("completed", "child-agent"))
            if data["case"] != "eof":
                events.append(
                    turn("failed" if data["case"] == "failed" else "completed")
                )
            body = "".join("data: " + json.dumps(e) + "\n\n" for e in events).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.flush()
            data["stream_open"].set()
            data["submitted"].wait(5)
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_DELETE(self):
            self.record()
            data["deletes"] += 1
            mode = data["case"]
            if mode == "conflict" and data["deletes"] == 1:
                self.reply(409, {"error": {"message": "still settling"}})
            elif mode == "missing":
                self.reply(404, {"error": {"message": "already removed"}})
            elif mode == "delete_error":
                self.reply(400, {"error": {"message": "test failure"}})
            else:
                self.reply(200, {"id": "sess-test", "deleted": mode != "unconfirmed"})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    data["base_url"] = f"http://127.0.0.1:{server.server_port}/v1"
    yield data
    server.shutdown()


# Both clients run against one fake server, so one set of assertions checks that they send the same requests.
@pytest.fixture(params=["python", "typescript"])
def runner(request, tmp_path, api):
    lang = request.param
    # The scripts read ../prompt.txt, so this layout keeps every file inside tmp_path.
    work = tmp_path / lang
    work.mkdir()
    for p in (SOURCE / lang).glob("*.py" if lang == "python" else "*.ts"):
        shutil.copy(p, work / p.name)
    if lang == "typescript":
        (work / "node_modules").symlink_to(
            SOURCE / "typescript/node_modules", target_is_directory=True
        )
        (work / "package.json").write_text('{"type":"module"}')
    if (SOURCE / "prompt.txt").exists():
        shutil.copy(SOURCE / "prompt.txt", tmp_path / "prompt.txt")
    binary = tmp_path / "bin"
    binary.mkdir()
    fake = binary / "render"
    fake.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$@" >> "$CLI_LOG"\nif [ "$3" = "list" ]; then printf \'[{"id":"sbx-test","status":"running"}]\\n\'; fi\n'
    )
    fake.chmod(0o755)
    env = {
        **os.environ,
        "OPENAI_API_KEY": "test-only",
        "OPENAI_BASE_URL": api["base_url"],
        "SANDBOX_ID": "sbx-test",
        "PATH": str(binary) + os.pathsep + os.environ["PATH"],
        "CLI_LOG": str(work / "cli.log"),
    }

    def run(name, *args, unset=()):
        cmd = (
            [sys.executable, str(work / (name + ".py"))]
            if lang == "python"
            else [
                str(SOURCE / "typescript/node_modules/.bin/tsx"),
                str(work / (name + ".ts")),
            ]
        )
        run_env = {k: v for k, v in env.items() if k not in unset}
        return subprocess.run(
            cmd + list(args),
            cwd=work,
            env=run_env,
            text=True,
            capture_output=True,
            timeout=15,
        )

    return run, work


def test_create_and_no_overwrite(runner, api):
    run, path = runner
    result = run("create_session")
    assert result.returncode == 0, result.stderr
    assert json.loads((path / "session.json").read_text()) == STATE
    assert (path / "session.json").stat().st_mode & 0o777 == 0o600
    assert run("create_session").returncode != 0
    assert len(api["requests"]) == 1


@pytest.mark.parametrize("case", ["ok", "failed", "eof", "submit_error"])
def test_task(runner, api, case):
    run, path = runner
    (path / "session.json").write_text(json.dumps(STATE))
    api["case"] = case
    result = run("run_task")
    assert (result.returncode == 0) == (case == "ok"), result.stderr
    assert ("Turn completed." in result.stdout) == (case == "ok")
    calls = api["requests"]
    assert [call[0] for call in calls] == ["GET", "POST"]
    headers = {k.lower(): v for k, v in calls[1][2].items()}
    assert headers.get("idempotency-key")
    cli = (path / "cli.log").read_text()
    assert "exec-server" in cli and STATE["environment_id"] in cli
    assert "test-only" not in cli
    assert (path / "session.json").exists()


def test_follow_up_does_not_launch_second_executor(runner, api):
    run, path = runner
    (path / "session.json").write_text(json.dumps(STATE))
    result = run("run_task", "Read hello.txt")
    assert result.returncode == 0, result.stderr
    assert not (path / "cli.log").exists()
    assert (
        api["requests"][1][3]["events"][0]["input"][0]["content"][0]["text"]
        == "Read hello.txt"
    )


@pytest.mark.parametrize(
    "case", ["ok", "conflict", "missing", "unconfirmed", "delete_error"]
)
def test_cleanup(runner, api, case):
    run, path = runner
    (path / "session.json").write_text(json.dumps(STATE))
    api["case"] = case
    result = run("cleanup")
    success = case in {"ok", "conflict", "missing"}
    assert (result.returncode == 0) == success, result.stderr
    assert (path / "session.json").exists() != success
    assert api["deletes"] == (2 if case == "conflict" else 1)


@pytest.mark.parametrize("name", ["run_task", "wait_for_sandbox"])
def test_missing_sandbox_id(runner, api, name):
    run, path = runner
    (path / "session.json").write_text(json.dumps(STATE))
    result = run(name, unset={"SANDBOX_ID"})
    assert result.returncode != 0
    assert "Set SANDBOX_ID first." in result.stderr
    assert "Traceback" not in result.stderr
    assert api["requests"] == []
    assert not (path / "cli.log").exists()


def test_readiness(runner):
    run, _ = runner
    result = run("wait_for_sandbox")
    assert result.returncode == 0, result.stderr
    assert "Sandbox is running." in result.stdout
