"""Регрессии ревью: память моделей, трубы процессов и сохранность результатов.

Без моделей, сети и ffmpeg: трубы проверяются короткими дочерними Python,
остальное — временными файлами и подставным движком.
"""
from __future__ import annotations

import io
import subprocess
import sys
import tempfile
import time
import types
import unittest
import weakref
from pathlib import Path
from unittest.mock import patch

import harness  # noqa: F401

from core import media
from core.asr.faster_whisper_backend import FasterWhisperBackend
from core.context import RunContext
from core.deps import fetch
from core.events import Cancelled, Code, CoreError, Kind
from core.job import Job, JobState
from core.pipeline import _already_done, run_job
from core.platform import Paths
from core.profile import TARGET_BOTH, TEMP_DELETE, TEMP_KEEP, Profile
from core.runner import JobRunner


class Resources(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="transcriber-resources-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.paths = Paths(self.root, *(self.root / name for name in
                           ("bin", "models", "temp", "logs", "profiles"))).ensure()
        self.tools = media.Tools(Path("ffmpeg"), Path("ffprobe"))
        self.events = []
        self.ctx = RunContext(self.paths, self.tools, None, self.events.append)

    def test_model_is_released_before_replacement(self):
        previous = []

        class Model:
            def __init__(self, *args, **kwargs):
                if previous:
                    assert previous[-1]() is None, "две модели одновременно в памяти"
                previous.append(weakref.ref(self))

        module = types.ModuleType("faster_whisper")
        module.WhisperModel = Model
        with patch.dict(sys.modules, faster_whisper=module):
            backend = FasterWhisperBackend()
            backend.load("small", "cpu", "int8")
            self.assertEqual(backend.load("small", "cpu", "int8"), 0.0)
            self.assertEqual(len(previous), 1)
            backend.load("medium", "cpu", "int8")
            backend.unload()
            self.assertIsNone(previous[-1]())

    def test_queue_reuses_then_releases_model(self):
        class Backend:
            loaded = False
            loads = 0

            def unload(self):
                self.loaded = False

        backend = Backend()

        def work(job, ctx):
            if not backend.loaded:
                backend.loads += 1
                backend.loaded = True
            job.state = JobState.DONE

        runner = JobRunner(paths=self.paths, tools=self.tools,
                           backend=backend, emit=self.events.append)
        runner.add(*(Job(self.root / f"{i}.wav", Profile()) for i in range(2)))
        with patch("core.runner.run_job", side_effect=work):
            runner.start()
            runner.join(2)
        self.assertFalse(runner.busy)
        self.assertEqual(backend.loads, 1)
        self.assertFalse(backend.loaded)
        self.assertEqual(self.events[-1].kind, Kind.QUEUE_DONE)
        self.assertEqual(self.events[-1].data["done"], 2)

    def test_silent_process_can_be_cancelled(self):
        started = time.monotonic()
        with self.assertRaises(Cancelled):
            media._run_ffmpeg(
                [sys.executable, "-c", "import time; time.sleep(5)"], 0, None,
                lambda: time.monotonic() - started >= 0.2)
        self.assertLess(time.monotonic() - started, 3)

    def test_stderr_is_drained_and_bounded(self):
        started = time.monotonic()
        code, error = media._run_ffmpeg(
            [sys.executable, "-c",
             "import sys; sys.stderr.write('x' * 2000000); sys.stderr.flush()"],
            0, None, lambda: time.monotonic() - started > 5)
        self.assertEqual(code, 0)
        self.assertTrue(error)
        self.assertLessEqual(len(error), 8192)

    def test_progress_callback_failure_stops_child(self):
        children = []
        popen = subprocess.Popen

        def spawn(*args, **kwargs):
            child = popen(*args, **kwargs)
            children.append(child)
            return child

        def fail(*args):
            raise ValueError("callback failed")

        with patch("core.media.subprocess.Popen", side_effect=spawn):
            with self.assertRaisesRegex(ValueError, "callback failed"):
                media._run_ffmpeg(
                    [sys.executable, "-c",
                     "import time; print('out_time_us=1000000', flush=True); time.sleep(5)"],
                    2, fail, None)
        self.assertIsNotNone(children[0].poll())
        self.assertTrue(children[0].stdout.closed)
        self.assertTrue(children[0].stderr.closed)

    def test_probe_timeout_has_domain_error(self):
        with patch("core.media.subprocess.run",
                   side_effect=subprocess.TimeoutExpired("ffprobe", 30)):
            with self.assertRaises(CoreError) as caught:
                media.probe(self.tools.ffprobe, self.root / "bad.wav")
        self.assertEqual(caught.exception.code, Code.FFPROBE_FAILED)
        self.assertEqual(caught.exception.data["reason"], "timeout")

    def test_audio_replacement_is_atomic_on_failure_and_success(self):
        source, target = self.root / "input.wav", self.root / "output.wav"
        source.write_bytes(b"source")
        target.write_bytes(b"previous result")
        for error in (Cancelled(), RuntimeError("callback failed")):
            with self.subTest(error=type(error).__name__):
                with patch("core.media._run_ffmpeg", side_effect=error):
                    with self.assertRaises(type(error)):
                        media.extract_audio(self.tools.ffmpeg, source, target)
                self.assertEqual(target.read_bytes(), b"previous result")
                self.assertEqual(list(self.root.glob(".transcriber-*")), [])

        def finish(cmd, *args):
            Path(cmd[-1]).write_bytes(b"a" * 2048)
            return 0, ""

        with patch("core.media._run_ffmpeg", side_effect=finish):
            media.extract_audio(self.tools.ffmpeg, source, target)
        self.assertEqual(target.read_bytes(), b"a" * 2048)
        self.assertEqual(list(self.root.glob(".transcriber-*")), [])

    def test_archive_copy_reads_bounded_chunks(self):
        class Bounded(io.BytesIO):
            def read(self, size=-1):
                assert 0 < size <= fetch.CHUNK, "бинарник читается целиком"
                return super().read(size)

        content = b"binary" * fetch.CHUNK
        with Bounded(content) as source:
            target = fetch._write(self.root / "ffmpeg", source)
        self.assertEqual(target.read_bytes(), content)

    def test_both_requires_audio_before_skipping(self):
        job = Job(self.root / "lecture.mp4", Profile(target=TARGET_BOTH))
        job.output(".txt").write_text("text", encoding="utf-8")
        self.assertFalse(_already_done(job, self.ctx))
        job.output(".wav").write_bytes(b"audio")
        self.assertTrue(_already_done(job, self.ctx))
        self.assertEqual(job.artifacts["audio"], job.output(".wav"))

    def test_failed_jobs_respect_temp_policy(self):
        for policy in (TEMP_DELETE, TEMP_KEEP):
            for error in (CoreError(Code.MODEL_LOAD_FAILED), ValueError("failed")):
                with self.subTest(policy=policy, error=type(error).__name__):
                    job = Job(self.root / "source.wav", Profile(temp_action=policy))
                    temp = self.paths.temp / "prepared.wav"

                    def prepare(job, ctx, temp=temp):
                        temp.write_bytes(b"temporary audio")
                        job.artifacts["temp_wav"] = temp
                        return temp

                    with patch("core.pipeline.probe.run"), \
                            patch("core.pipeline.prepare.run", side_effect=prepare), \
                            patch("core.pipeline.transcribe.run", side_effect=error):
                        run_job(job, self.ctx)
                    self.assertEqual(job.state, JobState.FAILED)
                    self.assertEqual(temp.exists(), policy == TEMP_KEEP)


if __name__ == "__main__":
    unittest.main()
