# Stage 1: Critical Fixes (Foundation for Conversational Mode)

**Audience:** Claude Code agent
**Repo:** https://github.com/Amar9827/ai_assistant (branch: `master`)
**Goal of this stage:** Fix the bugs that would actively break Stage 2 (the conversational rebuild), and replace the one component (subprocess Piper) whose latency floor is incompatible with conversational mode. Do **not** attempt continuous STT, endpointing, barge-in, or turn management here — that is Stage 2.

**Non-goal:** Making the app feel conversational. After Stage 1, the UX is the same walkie-talkie as today, but the substrate supports cancellation and the latency floor is much lower. The conversational experience is built on top of this in Stage 2.

---

## Why these specific fixes and not others

The original analysis listed 6 critical bugs. For Stage 1 we keep the ones that are either (a) prerequisites for Stage 2 or (b) cheap to do and would be re-broken by Stage 2 work if left in place. Bugs that get superseded by Stage 2's continuous-streaming architecture are deferred.

| Original bug | Stage 1? | Reason |
|---|---|---|
| LLM history corruption on disconnect | **Yes** | Stage 2 has many more cancellations than Stage 1. Bug goes from rare to constant. Foundational. |
| Sentence boundary parser | **No** | Stage 2 replaces sentence-based TTS with continuous overlapping TTS. Defer. |
| Piper subprocess per sentence | **Yes** | Subprocess startup cost is incompatible with conversational latency. Foundational. |
| CORS wide open | **Yes** | Cheap, security-relevant, no Stage 2 conflict. |
| Audio size cap missing | **Yes** | Same. |
| Temp file leak | **Yes** | Same. |
| Two parallel streaming implementations | **No** | Subsumed by Stage 2's turn manager. Defer. |

**New addition to Stage 1: cancellable TTS tasks.** Not in the original bug list, but required as a Stage 2 prerequisite. Without it, you cannot interrupt the assistant mid-response.

---

## What this stage delivers

1. LLM conversation history is atomic — never half-committed on disconnect or cancellation.
2. Piper TTS runs in-process (one Python process, one ONNX session load), with the user's `PIPER_SPEAKER` setting preserved across the migration.
3. Every TTS generation runs inside a cancellable `asyncio.Task` attached to the current turn. Calling `turn.cancel()` stops all pending TTS within ~50 ms.
4. CORS is locked to a configurable allowlist; audio uploads are size-capped; temp files are cleaned up on any exit path.
5. `.env.example`, `README.md`, and `PERFORMANCE.md` all agree about the same defaults — no more pre-flight blockers from documentation drift.
6. No regressions to existing UX, frontend wire format, wake-word integration, CLI, or examples.

---

## Pre-flight checklist (run before any code changes)

Before starting Phase 0, the agent must confirm the following so we don't ship a regression:

1. **Capture baseline.** Start backend + frontend + Ollama. Run one voice query. Note (a) time-to-first-audio after clicking Stop, (b) which Piper voice/speaker is actually in `.env` (per the README, should be `en_GB-vctk-medium` speaker 17). Save these in `BASELINE.txt` at repo root — gitignore it.
2. **Resolve config drift first.** The README documents `PIPER_VOICE=en_GB-vctk-medium` but `.env.example` (and possibly the user's `.env`) may say `en_US-lessac-medium`. If the user's `.env` points at a voice that doesn't exist in `models/piper/`, **stop and tell the user**. Two paths:
   - **Path A (recommended):** Update `.env` to match the README and an installed voice (`PIPER_VOICE=en_GB-vctk-medium`, `PIPER_SPEAKER=17`). This also exercises the multi-speaker code path that Phase 2's speaker probe is designed to protect.
   - **Path B:** Download the configured voice file (see README installation step 3).
3. **Confirm `piper-tts` installed version.** Run `pip show piper-tts | grep Version`. Record the version in `BASELINE.txt`. If it returns 1.2.x, note that Phase 2 will require upgrading to ≥1.3.0 — a breaking API change in the upstream package. If 1.3.x+, Phase 2's migration is straightforward.
4. **Note Python version.** `python --version`. If < 3.10, stop — the codebase requires 3.10+.
5. **Verify Piper voice file exists** at `models/piper/<PIPER_VOICE>.onnx` plus `.onnx.json` companion. If not, stop after step 2's fix.

Do not skip these. The Piper migration in Phase 2 is the riskiest part of this stage and the probe results determine the exact code path.

---

## Phase 0 — Branch and test scaffolding

**Goal:** Don't lose work. Set up the test harness so subsequent phases can add tests as they go.

### Tasks

1. `git checkout -b stage1-critical-fixes`.
2. Add to `requirements.txt`:
   ```
   pytest>=8.0
   pytest-asyncio>=0.23
   ```
3. Create `tests/conftest.py`:
   ```python
   import pytest
   from pathlib import Path
   from config.settings import Settings

   @pytest.fixture
   def settings(tmp_path, monkeypatch):
       """Settings pointing at a temp dir so tests don't need real models."""
       monkeypatch.setenv("OLLAMA_HOST", "http://test-fake:11434")
       s = Settings()
       # Override paths to tmp
       s.MODELS_DIR = tmp_path / "models"
       s.MODELS_DIR.mkdir(parents=True, exist_ok=True)
       (s.MODELS_DIR / "piper").mkdir(exist_ok=True)
       return s
   ```
4. Add a `pytest.ini` at repo root:
   ```ini
   [pytest]
   testpaths = tests
   asyncio_mode = auto
   filterwarnings =
       ignore::DeprecationWarning
   ```
5. Verify it runs: `pytest -v` should report 0 tests collected, no errors.

✅ **Commit:** `chore: add pytest scaffolding for stage 1`

---

## Phase 1 — LLM history atomic commit

**File:** `src/core/llm.py`
**Bug:** `generate_response(stream=True)` calls `self.conversation_history.append(user_msg)` at line 36 *before* returning the generator. The assistant reply is appended at line 80 inside `_stream_response`, but only if the generator runs to completion. On WebSocket disconnect or cancellation mid-stream, history is left with an orphaned user turn. Every subsequent turn references corrupted context.

**Constraint:** All 5 callers (`assistant.py:65`, `assistant.py:139` via `generate_streaming_sentences`, `assistant.py:158`, `server.py:384`, plus `conversation_demo.py` which reads `.conversation_history` at line 39) must keep working without modification. This is an internal-only fix — no public signature changes.

### Tasks

1. **Rewrite `generate_response` and `_stream_response` in `src/core/llm.py`** so history mutation is atomic. Key principle: build the message list using `pending_user` *without* mutating `self.conversation_history`, then commit both turns in a `finally` block, but only if at least some response content was produced.

   Replace lines 25–82 (the two methods) with:

   ```python
   def generate_response(self, user_input: str, stream: bool = False):
       """
       Generate response from LLM.

       Returns str if stream=False, Generator[str] if stream=True.
       History is committed atomically: either both user and assistant
       turns are appended, or neither is (e.g., on disconnect mid-stream).
       """
       pending_user = {"role": "user", "content": user_input}
       messages = [self.system_prompt] + self.conversation_history + [pending_user]

       response = self.client.chat(
           model=self.settings.OLLAMA_MODEL,
           messages=messages,
           options={"temperature": self.settings.OLLAMA_TEMPERATURE},
           stream=stream,
       )

       if stream:
           return self._stream_response(response, pending_user)

       # Non-streaming path: commit both turns now.
       assistant_message = response["message"]["content"]
       self.conversation_history.append(pending_user)
       self.conversation_history.append(
           {"role": "assistant", "content": assistant_message}
       )
       self._cap_history()
       return assistant_message

   def _stream_response(self, response, pending_user):
       """
       Stream chunks while accumulating the full assistant reply.

       On generator close (GeneratorExit), normal completion, or any
       other exit: commit both user and assistant turns IF any content
       was produced. If zero chunks were yielded (immediate disconnect),
       commit nothing — leave history clean.
       """
       full_response = ""
       try:
           for chunk in response:
               content = chunk["message"]["content"]
               full_response += content
               yield content
       finally:
           if full_response.strip():
               self.conversation_history.append(pending_user)
               self.conversation_history.append(
                   {"role": "assistant", "content": full_response}
               )
               self._cap_history()

   def _cap_history(self):
       """Trim conversation_history to last N turns (N user + N assistant msgs)."""
       max_msgs = self.max_history_turns * 2
       if len(self.conversation_history) > max_msgs:
           self.conversation_history = self.conversation_history[-max_msgs:]
   ```

2. **Add a history cap.** Add to `LLMProcessor.__init__`:
   ```python
   self.max_history_turns = getattr(settings, "MAX_HISTORY_TURNS", 20)
   ```

3. **Add `MAX_HISTORY_TURNS` to `config/settings.py`:**
   ```python
   MAX_HISTORY_TURNS: int = 20
   ```

4. **Tests** — create `tests/test_llm.py`:

   ```python
   import pytest
   from unittest.mock import MagicMock
   from src.core.llm import LLMProcessor

   class FakeOllamaResponse:
       """Fake Ollama streaming response — yields preset chunks."""
       def __init__(self, chunks):
           self.chunks = chunks
       def __iter__(self):
           for c in self.chunks:
               yield {"message": {"content": c}}

   def _make_llm(settings, response):
       llm = LLMProcessor(settings)
       llm.client = MagicMock()
       llm.client.chat = MagicMock(return_value=response)
       return llm

   def test_streaming_full_consumption_commits_both_turns(settings):
       llm = _make_llm(settings, FakeOllamaResponse(["Hello", " world", "!"]))
       chunks = list(llm.generate_response("Hi", stream=True))
       assert "".join(chunks) == "Hello world!"
       assert llm.conversation_history == [
           {"role": "user", "content": "Hi"},
           {"role": "assistant", "content": "Hello world!"},
       ]

   def test_streaming_partial_consumption_still_commits(settings):
       """If consumer stops early (simulates disconnect), partial reply still commits."""
       llm = _make_llm(settings, FakeOllamaResponse(["Hello", " world", "!"]))
       gen = llm.generate_response("Hi", stream=True)
       got = next(gen)
       gen.close()  # Simulates client disconnect mid-stream
       assert got == "Hello"
       # History should have BOTH turns, with assistant content = what was yielded
       assert llm.conversation_history == [
           {"role": "user", "content": "Hi"},
           {"role": "assistant", "content": "Hello"},
       ]

   def test_streaming_zero_chunks_commits_nothing(settings):
       """If generator closes before yielding anything, history is untouched."""
       llm = _make_llm(settings, FakeOllamaResponse([]))
       gen = llm.generate_response("Hi", stream=True)
       gen.close()
       assert llm.conversation_history == []

   def test_non_streaming_commits_atomically(settings):
       llm = _make_llm(settings, {"message": {"content": "Hi there"}})
       result = llm.generate_response("Hello")
       assert result == "Hi there"
       assert llm.conversation_history == [
           {"role": "user", "content": "Hello"},
           {"role": "assistant", "content": "Hi there"},
       ]

   def test_history_is_capped(settings):
       llm = LLMProcessor(settings)
       llm.max_history_turns = 3  # Cap at 3 turns = 6 messages
       llm.client = MagicMock()
       for i in range(10):
           llm.client.chat = MagicMock(return_value={"message": {"content": f"reply{i}"}})
           llm.generate_response(f"q{i}")
       assert len(llm.conversation_history) == 6  # 3 turns * 2 messages
       # Last user message should be q9
       assert llm.conversation_history[-2] == {"role": "user", "content": "q9"}
   ```

5. **Verify `generate_streaming_sentences` still works.** It's a one-line passthrough at `llm.py:92`. No changes needed — confirm by reading it. Also confirm `server.py:384` (`for chunk in llm.generate_response(user_text, stream=True)`) still works — it does because the generator interface is preserved.

### Acceptance criteria

- [ ] `pytest tests/test_llm.py -v` — all 5 tests pass.
- [ ] Mid-stream disconnect followed by a new query produces a coherent response (manual smoke test: start a long query in the web UI, close the browser tab while assistant is speaking, reopen, ask a follow-up — assistant should not appear "confused" by orphaned context).
- [ ] No changes to `generate_response` callsite signatures.

✅ **Commit:** `fix(llm): commit history atomically across stream lifecycle`

---

## Phase 2 — Piper TTS in-process (highest-risk phase)

**File:** `src/core/tts.py` + `requirements.txt` + small changes to `assistant.py` and `server.py` callers.
**Bug:** `synthesize()` shells out to `python -m piper` *per sentence*. Each call cold-starts a Python interpreter and loads the ONNX model from disk. This dominates TTS latency and is incompatible with conversational mode.

**Risk:** The `piper-tts` package had a breaking API change between 1.2.x (old `rhasspy/piper`) and 1.3.0+ (new `OHF-Voice/piper1-gpl`). The repo currently pins `piper-tts>=1.2.0`, which means whatever was installed is unknown. The new API supports the streaming `synthesize() -> Iterator[AudioChunk]` interface we need; the old one does not.

**Additional risk:** The README documents using `en_GB-vctk-medium` (109 speakers) with `PIPER_SPEAKER=17`. The new API's speaker selection mechanism is version-dependent. We must probe and fall back gracefully or the user's voice silently regresses to speaker 0.

### Tasks

1. **Pin Piper version explicitly** in `requirements.txt`:
   ```diff
   - piper-tts>=1.2.0              # Piper TTS
   + piper-tts>=1.3.0,<2.0         # Piper TTS (1.3.0+ API: AudioChunk streaming)
   ```
   Mirror in `setup.py`.

2. **Upgrade the user's venv.** After the requirements change, run `pip install -U 'piper-tts>=1.3.0,<2.0'`. Confirm with `pip show piper-tts | grep Version`. Add the post-upgrade version to `BASELINE.txt`.

3. **Rewrite `src/core/tts.py`.** Full replacement (keep the class name and `initialize`/`synthesize` signatures; add `synthesize_chunks`):

   ```python
   """
   In-process Piper TTS using the piper-tts >=1.3.0 Python API.

   This module loads PiperVoice once at startup and reuses the ONNX session
   for every synthesize() call, eliminating the per-sentence subprocess
   overhead of the legacy implementation.
   """
   import logging
   from pathlib import Path
   from typing import Iterator, Optional

   import numpy as np

   from config.settings import Settings

   logger = logging.getLogger(__name__)


   class TextToSpeech:
       def __init__(self, settings: Settings):
           self.settings = settings
           self.model_path: Path = settings.PIPER_MODEL_PATH
           self.voice = None
           self.sample_rate: int = 22050  # Overwritten on initialize()
           self._speaker_id: Optional[int] = None
           self._speaker_kwarg_supported: Optional[bool] = None

       @property
       def last_sample_rate(self) -> int:
           """Backward-compat alias for existing callers in assistant.py and server.py.

           The legacy subprocess implementation only knew the sample rate AFTER
           synthesizing (it was read from the output WAV header), hence the name.
           In the new implementation we know it at load time, but we keep this
           property to avoid touching every callsite.
           """
           return self.sample_rate

       def initialize(self):
           """Load the Piper voice model. Called once at startup."""
           if not self.model_path.exists():
               raise FileNotFoundError(
                   f"Piper model not found: {self.model_path}\n"
                   f"Download it per README and ensure PIPER_VOICE matches the filename."
               )

           try:
               from piper import PiperVoice
           except ImportError as e:
               raise RuntimeError(
                   "piper-tts package not importable. Run: pip install -U 'piper-tts>=1.3.0,<2.0'"
               ) from e

           logger.info("Loading Piper voice: %s", self.model_path)
           self.voice = PiperVoice.load(str(self.model_path))
           self.sample_rate = self.voice.config.sample_rate

           # Detect speaker support. Configured speaker may not be honored if
           # (a) voice is single-speaker, or (b) the installed Piper version
           # doesn't accept speaker_id on synthesize(). We probe once.
           configured_speaker = getattr(self.settings, "PIPER_SPEAKER", 0)
           if configured_speaker and configured_speaker != 0:
               self._probe_speaker_support(configured_speaker)
           else:
               self._speaker_id = None
               self._speaker_kwarg_supported = False

           logger.info(
               "Piper initialized: sample_rate=%d, speaker_id=%s, kwarg_supported=%s",
               self.sample_rate, self._speaker_id, self._speaker_kwarg_supported,
           )

       def _probe_speaker_support(self, speaker_id: int):
           """Try calling synthesize() with speaker_id; fall back if not supported."""
           try:
               # Drain one chunk to test signature.
               gen = self.voice.synthesize("test", speaker_id=speaker_id)
               _ = next(iter(gen), None)
               self._speaker_id = speaker_id
               self._speaker_kwarg_supported = True
               logger.info("Speaker selection via speaker_id=%d works.", speaker_id)
           except TypeError:
               logger.warning(
                   "Installed piper-tts does not accept speaker_id kwarg on synthesize(). "
                   "PIPER_SPEAKER=%d will be IGNORED. Voice falls back to speaker 0.",
                   speaker_id,
               )
               self._speaker_id = None
               self._speaker_kwarg_supported = False
           except Exception as e:
               logger.warning(
                   "Speaker probe failed (%s). Falling back to speaker 0.", e,
               )
               self._speaker_id = None
               self._speaker_kwarg_supported = False

       def _synth_kwargs(self) -> dict:
           if self._speaker_kwarg_supported and self._speaker_id is not None:
               return {"speaker_id": self._speaker_id}
           return {}

       def synthesize(self, text: str) -> np.ndarray:
           """
           Synthesize text to a complete int16 PCM numpy array.

           Buffers all chunks. Call from a thread (asyncio.to_thread) to keep
           the event loop responsive.
           """
           if self.voice is None:
               raise RuntimeError("TTS not initialized; call initialize() first")
           buf = bytearray()
           for chunk in self.voice.synthesize(text, **self._synth_kwargs()):
               buf.extend(chunk.audio_int16_bytes)
           return np.frombuffer(bytes(buf), dtype=np.int16)

       def synthesize_chunks(self, text: str) -> Iterator[np.ndarray]:
           """
           Yield int16 PCM numpy arrays as Piper produces them.

           Useful for streaming to the WebSocket without buffering the whole
           utterance. Stage 1 callers still use synthesize(); this is for Stage 2.
           """
           if self.voice is None:
               raise RuntimeError("TTS not initialized; call initialize() first")
           for chunk in self.voice.synthesize(text, **self._synth_kwargs()):
               yield np.frombuffer(chunk.audio_int16_bytes, dtype=np.int16)

       def synthesize_to_file(self, text: str, output_path: str):
           """Compatibility shim — writes a WAV file using the in-process API."""
           import wave
           if self.voice is None:
               raise RuntimeError("TTS not initialized; call initialize() first")
           with wave.open(output_path, "wb") as wav_file:
               self.voice.synthesize_wav(text, wav_file, **self._synth_kwargs())
   ```

4. **Verify no caller is broken.** Cross-check every callsite for `tts.synthesize` and `tts.last_sample_rate`:
   - `src/core/assistant.py:70, 127, 161`: call `self.tts.synthesize(text)` → returns `np.ndarray`, same as before. ✓
   - `src/core/assistant.py:72, 128`: read `self.tts.last_sample_rate` → now a property returning `self.sample_rate`. Same int value. ✓
   - `backend/server.py:240`: `await asyncio.to_thread(tts.synthesize, text)` → unchanged. ✓
   - `backend/server.py:255`: read `tts.last_sample_rate` → property. ✓

   No caller code changes needed. This is deliberate.

5. **Tests** — create `tests/test_tts.py`:

   ```python
   import os
   import pytest
   import numpy as np
   from pathlib import Path

   # Skip the whole module if piper isn't installed.
   pytest.importorskip("piper")

   from src.core.tts import TextToSpeech

   # Locate a model file. Prefer env override, then the README-documented voice,
   # then any *.onnx under models/piper.
   _REPO_ROOT = Path(__file__).parent.parent
   _CANDIDATES = [
       Path(os.environ.get("PIPER_MODEL_PATH", "")) if os.environ.get("PIPER_MODEL_PATH") else None,
       _REPO_ROOT / "models" / "piper" / "en_GB-vctk-medium.onnx",
       *sorted((_REPO_ROOT / "models" / "piper").glob("*.onnx")),
   ]
   MODEL_PATH = next((p for p in _CANDIDATES if p and p.exists()), None)

   if MODEL_PATH is None:
       pytest.skip("No Piper model present under models/piper/", allow_module_level=True)

   @pytest.fixture
   def tts(settings):
       settings.PIPER_VOICE = MODEL_PATH.stem
       t = TextToSpeech(settings)
       t.model_path = MODEL_PATH  # override property-derived path
       t.initialize()
       return t

   def test_initialize_loads_voice_and_sample_rate(tts):
       assert tts.voice is not None
       assert tts.sample_rate > 0
       assert tts.last_sample_rate == tts.sample_rate  # backward-compat property

   def test_synthesize_returns_int16_numpy_array(tts):
       audio = tts.synthesize("Hello, this is a test.")
       assert isinstance(audio, np.ndarray)
       assert audio.dtype == np.int16
       assert len(audio) > 0

   def test_synthesize_chunks_yields_same_total(tts):
       text = "This is a longer test sentence that should produce multiple chunks."
       full = tts.synthesize(text)
       chunked = np.concatenate(list(tts.synthesize_chunks(text)))
       # Sample counts should match exactly (deterministic synthesis at temp=0)
       # If they don't match (non-determinism), at least within 1% length.
       assert abs(len(full) - len(chunked)) / len(full) < 0.01

   def test_speaker_probe_doesnt_crash(tts):
       """Init succeeds regardless of whether speaker_id is supported."""
       assert tts._speaker_kwarg_supported in (True, False)
   ```

### Acceptance criteria

- [ ] `pip install -U 'piper-tts>=1.3.0,<2.0'` succeeds in the project venv.
- [ ] Running the backend produces a startup log line confirming Piper initialized, with `speaker_id` and `kwarg_supported` flags visible.
- [ ] If `PIPER_SPEAKER` is set in `.env` and is unsupported, a `WARNING` log line is printed (do not fail startup).
- [ ] One real voice query end-to-end produces audio at the same voice the user heard pre-migration (manual ear-check against `BASELINE.txt`). If the voice changed, the speaker probe is broken — investigate before merging.
- [ ] `pytest tests/test_tts.py -v` — all tests pass *or skip cleanly* if the model file isn't installed.
- [ ] No `subprocess` call to Piper anywhere in `src/` or `backend/` (grep `subprocess.*piper` returns empty).
- [ ] TTS-per-sentence latency improved by ≥3× vs baseline. **Record the measured new latency in `BASELINE.txt` — Phase 5 needs it.**

✅ **Commit:** `perf(tts): replace subprocess with in-process PiperVoice; preserve speaker selection`

---

## Phase 3 — Cancellable TTS tasks (Stage 2 prerequisite)

**Files:** `backend/server.py`
**Why:** Stage 2 needs to interrupt assistant audio when the user starts speaking. That requires every TTS generation to be a structured, cancellable task — not a sequential `await` chain. Stage 1 adds the cancellation primitive; nothing actually cancels it yet (that's Stage 2). But the primitive must exist now so Stage 2 isn't a rewrite of `handle_voice_query`.

**Constraint:** UX is unchanged. Frontend wire format is unchanged. No new message types.

### Tasks

1. **Introduce a `Turn` dataclass.** Add to `backend/server.py` near the top, after imports:

   ```python
   import uuid
   from dataclasses import dataclass, field
   from typing import Set
   import asyncio

   @dataclass
   class Turn:
       """One user→assistant exchange. Owns all in-flight tasks for that exchange.

       Stage 1: we create a Turn per query but never call cancel() on it.
       Stage 2: barge-in detection will call turn.cancel() the instant the user
       starts speaking, stopping pending TTS within ~50ms.
       """
       id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
       tasks: Set[asyncio.Task] = field(default_factory=set)
       _cancelled: bool = False

       def spawn(self, coro) -> asyncio.Task:
           """Run coro as a tracked task on this turn."""
           task = asyncio.create_task(coro)
           self.tasks.add(task)
           task.add_done_callback(self.tasks.discard)
           return task

       def cancel(self):
           """Cancel all in-flight tasks for this turn."""
           self._cancelled = True
           for t in list(self.tasks):
               if not t.done():
                   t.cancel()

       @property
       def cancelled(self) -> bool:
           return self._cancelled

       async def wait_all(self):
           """Wait for all tracked tasks to complete (or be cancelled)."""
           if not self.tasks:
               return
           await asyncio.gather(*self.tasks, return_exceptions=True)
   ```

2. **Refactor `handle_voice_query` in `backend/server.py`** to use a `Turn` and to spawn TTS as a tracked task (still awaited sequentially in Stage 1 — Stage 2 will make it concurrent).

   Replace the existing function (currently at `server.py:354`) with:

   ```python
   async def handle_voice_query(websocket: WebSocket, user_text: str):
       """
       Process a query end-to-end. All TTS work runs as tasks on a Turn
       object so Stage 2 can cancel it for barge-in.
       """
       turn = Turn()
       try:
           await websocket.send_json({"type": "status", "status": "processing"})
           print(f"[USER turn={turn.id}] {user_text}")

           full_response = ""
           current_sentence = ""
           audio_started = False

           for chunk in llm.generate_response(user_text, stream=True):
               if turn.cancelled:
                   break

               full_response += chunk
               current_sentence += chunk

               await websocket.send_json({"type": "transcript", "text": full_response})

               # Stage 1 keeps the original sentence detection. Stage 2 replaces
               # this entire block with continuous overlapping TTS via SentenceBuffer.
               if any(p in chunk for p in [". ", "! ", "? ", "\n"]):
                   sentence = current_sentence.strip()
                   if sentence:
                       if not audio_started:
                           await websocket.send_json({"type": "status", "status": "speaking"})
                           audio_started = True
                       # Spawn TTS as a tracked task; await it immediately for Stage 1.
                       # Stage 2 will let it run concurrently with the next iteration.
                       task = turn.spawn(generate_and_stream_audio(websocket, sentence, turn))
                       try:
                           await task
                       except asyncio.CancelledError:
                           break
                   current_sentence = ""

               await asyncio.sleep(0.02)

           if current_sentence.strip() and not turn.cancelled:
               if not audio_started:
                   await websocket.send_json({"type": "status", "status": "speaking"})
               task = turn.spawn(
                   generate_and_stream_audio(websocket, current_sentence.strip(), turn)
               )
               try:
                   await task
               except asyncio.CancelledError:
                   pass

           print(f"[AI turn={turn.id}] {full_response}")

           if not turn.cancelled:
               await websocket.send_json({"type": "response", "response": full_response})
               await websocket.send_json({"type": "status", "status": "connected"})

       except Exception as e:
           print(f"[ERROR turn={turn.id}] {e}")
           import traceback
           traceback.print_exc()
           try:
               await websocket.send_json({"type": "status", "status": "error"})
           except Exception:
               pass
       finally:
           # Ensure no orphan tasks survive the turn.
           turn.cancel()
           await turn.wait_all()
   ```

3. **Make `generate_and_stream_audio` cancellation-aware.** Modify the existing function (at `server.py:223`) to check `turn.cancelled` between chunk sends and to handle `CancelledError` cleanly:

   ```python
   async def generate_and_stream_audio(websocket: WebSocket, text: str, turn: "Turn"):
       """Generate TTS for one sentence and stream chunks. Cancellable."""
       try:
           audio_array = await asyncio.to_thread(tts.synthesize, text)
           print(f"[TTS turn={turn.id}] Generated {len(audio_array)} samples")

           CHUNK_SIZE = 8192
           for i in range(0, len(audio_array), CHUNK_SIZE):
               if turn.cancelled:
                   return
               chunk = audio_array[i:i + CHUNK_SIZE]
               import base64
               chunk_base64 = base64.b64encode(chunk.tobytes()).decode()
               await websocket.send_json({
                   "type": "audio_chunk",
                   "audio": chunk_base64,
                   "sample_rate": tts.last_sample_rate,
                   "dtype": "int16",
               })
               await asyncio.sleep(0.02)
       except asyncio.CancelledError:
           print(f"[TTS turn={turn.id}] Cancelled mid-stream")
           raise
       except Exception as e:
           print(f"[TTS ERROR turn={turn.id}] {e}")
   ```

4. **Tests** — create `tests/test_turn.py`:

   ```python
   import asyncio
   import pytest
   from backend.server import Turn

   @pytest.mark.asyncio
   async def test_turn_spawns_and_tracks_tasks():
       turn = Turn()
       async def work():
           await asyncio.sleep(0.01)
           return "done"
       task = turn.spawn(work())
       result = await task
       assert result == "done"
       assert task not in turn.tasks  # done_callback removes it

   @pytest.mark.asyncio
   async def test_turn_cancel_stops_inflight_tasks():
       turn = Turn()
       started = asyncio.Event()
       async def long_work():
           started.set()
           await asyncio.sleep(10)
       task = turn.spawn(long_work())
       await started.wait()
       turn.cancel()
       with pytest.raises(asyncio.CancelledError):
           await task
       assert turn.cancelled

   @pytest.mark.asyncio
   async def test_wait_all_returns_even_on_cancellation():
       turn = Turn()
       async def long_work():
           await asyncio.sleep(10)
       turn.spawn(long_work())
       turn.spawn(long_work())
       turn.cancel()
       await turn.wait_all()  # Should not hang
   ```

### Acceptance criteria

- [ ] `pytest tests/test_turn.py -v` — all 3 tests pass.
- [ ] Existing UX unchanged: voice query, text query, response streaming all work identically to baseline.
- [ ] No new WebSocket message types added to the frontend contract.
- [ ] Logs include `turn=<id>` for each query — useful for Stage 2 debugging.

✅ **Commit:** `feat(server): add Turn primitive with cancellable TTS tasks`

---

## Phase 4 — CORS lockdown, audio size cap, temp file cleanup

**File:** `backend/server.py`, `config/settings.py`, `.env.example`.
**Bugs:**
- `allow_origins=["*"]` + `allow_credentials=True` is invalid per CORS spec; some browsers reject it.
- `handle_audio_data` accepts unbounded base64 audio and writes it straight to disk.
- Temp file at `server.py:308` is only deleted on the success path. If `stt.transcribe_file` raises, it leaks.
- `audio_format` is taken from untrusted input and used directly in a file suffix.

### Tasks

1. **Add settings.** In `config/settings.py`:
   ```python
   CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
   MAX_AUDIO_MB: int = 25  # Per-request audio upload cap
   ```
   Note: keep as comma-separated string in env, parse to list at use site. `pydantic-settings` 2.x supports lists but the simplest interop with `.env` files is CSV.

2. **Update `.env.example`** — add the new vars *and* fix the existing config drift the pre-flight flagged. See Phase 5 for the full `.env.example` rewrite.

3. **Update CORS middleware in `backend/server.py`** (currently lines 41–47). Replace:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
       allow_credentials=False,
       allow_methods=["GET", "POST"],
       allow_headers=["*"],
   )
   ```

4. **Add audio size validation in `handle_audio_data`** (currently at `server.py:280`). At the top of the function, after reading `audio_base64`:

   ```python
   ALLOWED_FORMATS = {"webm", "wav", "ogg", "mp3"}
   max_bytes = settings.MAX_AUDIO_MB * 1024 * 1024

   audio_base64 = data.get("audio", "")
   audio_format = data.get("format", "webm").lower()

   if not audio_base64:
       print("[ERROR] No audio data received")
       return

   if audio_format not in ALLOWED_FORMATS:
       print(f"[ERROR] Rejected audio_format: {audio_format!r}")
       await websocket.send_json({
           "type": "status", "status": "error",
           "message": f"Unsupported audio format: {audio_format}",
       })
       return

   # base64 encodes 3 bytes → 4 chars, so decoded size ≈ len * 0.75
   if len(audio_base64) * 0.75 > max_bytes:
       print(f"[ERROR] Audio too large: ~{len(audio_base64) * 0.75 / 1024 / 1024:.1f} MB")
       await websocket.send_json({
           "type": "status", "status": "error",
           "message": f"Audio exceeds {settings.MAX_AUDIO_MB} MB cap",
       })
       return
   ```

5. **Fix the temp file leak.** Replace the existing `tempfile`/`unlink` pattern (lines 306–321) with a `try/finally`:

   ```python
   tmp_path = None
   try:
       audio_bytes = base64.b64decode(audio_base64)
       print(f"[AUDIO] Decoded {len(audio_bytes)} bytes")

       with tempfile.NamedTemporaryFile(suffix=f".{audio_format}", delete=False) as f:
           f.write(audio_bytes)
           tmp_path = f.name

       user_text = await asyncio.to_thread(stt.transcribe_file, tmp_path)
   finally:
       if tmp_path:
           Path(tmp_path).unlink(missing_ok=True)
   ```

6. **Tests** — create `tests/test_server_security.py`:

   ```python
   import base64
   import pytest
   from fastapi.testclient import TestClient

   # Import lazily to avoid triggering module-level initialization during collection.
   def _client():
       from backend.server import app
       return TestClient(app)

   def test_cors_origin_not_wildcard():
       client = _client()
       r = client.get("/", headers={"Origin": "https://evil.example"})
       # Wildcard would echo any origin; allowlist won't.
       assert r.headers.get("access-control-allow-origin") != "*"

   def test_cors_allows_localhost_5173():
       client = _client()
       r = client.options(
           "/wake-word/status",
           headers={
               "Origin": "http://localhost:5173",
               "Access-Control-Request-Method": "GET",
           },
       )
       assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"
   ```

   Add a unit test for size validation if test infrastructure permits (would require mocking the WebSocket flow — defer if complex; the manual smoke test below covers it).

### Acceptance criteria

- [ ] Backend starts; `curl -i http://localhost:8000/` shows no `access-control-allow-origin: *`.
- [ ] Setting `CORS_ORIGINS` in `.env` to a custom origin works; frontend on that origin connects.
- [ ] Sending an oversized audio payload via the WebSocket produces an `error` status, not a crash.
- [ ] If transcription is forced to fail (manually raise inside `stt.transcribe_file`), the temp file at `/tmp/*.webm` is still deleted (`ls /tmp/*.webm` after the failed request returns nothing related to the request).
- [ ] Wake-word integration still works: `curl -X POST localhost:8000/wake-word/trigger` triggers the connected frontend.

✅ **Commit:** `fix(server): lock CORS, cap audio size, fix temp file leak`

---

## Phase 5 — Verification, doc sync, and performance update

This phase ends the stage by aligning every piece of documentation with what's now actually true. The repo currently has three different sources of truth disagreeing about defaults (`.env.example`, `README.md`, in-code defaults). Stage 1 fixes that.

### Tasks

1. **Run the full test suite:** `pytest -v`. All Stage 1 tests must pass (Piper tests skip cleanly if model not present).

2. **End-to-end manual smoke test** (do not skip):
   - Start Ollama, backend, frontend.
   - Voice query in the default voice — confirm audio sounds identical to baseline (compare with `BASELINE.txt` notes).
   - Voice query, then mid-response close the browser tab. Reopen, ask a follow-up. Assistant should not act confused (LLM history is clean).
   - Start `python run_wake_word.py` in a third terminal. Trigger via voice ("Hey Jarvis") *and* via `curl -X POST http://localhost:8000/wake-word/trigger`. Frontend should auto-start recording in both cases.
   - Send a fake `audio_data` message with `format: "exe"` from the browser console. Server should reject cleanly, not crash.
   - Run `python examples/simple_query.py` and `python examples/conversation_demo.py`. Both should complete without error.
   - Run `python -m src.interfaces.cli` (or `assistant-cli` if entry point is installed). Voice mode and text mode both work.

3. **Measure performance and update `PERFORMANCE.md`.** New time-to-first-audio should be significantly lower than baseline. Record the actual measured number — don't guess.

4. **Sync `.env.example` with reality.** Replace its contents with:

   ```bash
   # AI Voice Assistant Configuration
   # Copy this file to .env and customize for your system

   # ─── Speech-to-Text (Whisper) ───────────────────────────────────────
   # Options: tiny, base, small, medium, large
   # Recommendation: small (balanced accuracy and speed)
   WHISPER_MODEL=small
   WHISPER_DEVICE=auto
   WHISPER_COMPUTE_TYPE=int8

   # ─── Language Model (Ollama) ────────────────────────────────────────
   # Install models with: ollama pull <model-name>
   # Fast: llama3.2:3b (3-7s) | Balanced: mistral:7b (6-10s) | Quality: llama3.1:8b
   OLLAMA_MODEL=llama3.2:3b
   OLLAMA_HOST=http://localhost:11434
   OLLAMA_TEMPERATURE=0.7

   # Maximum conversation history turns to retain (each turn = user + assistant)
   MAX_HISTORY_TURNS=20

   # ─── Text-to-Speech (Piper) ─────────────────────────────────────────
   # PIPER_VOICE must match a downloaded model in models/piper/<name>.onnx
   # Download voices: https://github.com/rhasspy/piper/blob/master/VOICES.md
   # README recommends en_GB-vctk-medium (109 speakers) with speaker 17
   PIPER_VOICE=en_GB-vctk-medium
   PIPER_SPEAKER=17

   # ─── Wake Word ──────────────────────────────────────────────────────
   # Lower threshold = more sensitive (0.15-0.30 range; 0.22 is balanced)
   WAKE_WORD_THRESHOLD=0.22
   WAKE_WORD_DEBOUNCE=2.0

   # ─── Audio I/O ──────────────────────────────────────────────────────
   SAMPLE_RATE=16000

   # ─── Server hardening ───────────────────────────────────────────────
   # Comma-separated list of allowed frontend origins
   CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
   # Maximum audio upload size per request, in megabytes
   MAX_AUDIO_MB=25
   ```

   Key changes vs current `.env.example`:
   - `PIPER_VOICE` now matches the README and the disk reality.
   - `PIPER_SPEAKER` is now present (was missing).
   - `OLLAMA_MODEL` default aligned with README's "fast" option.
   - `WAKE_WORD_*` vars exposed (were hardcoded in `wake_word_local.py`).
   - `MAX_HISTORY_TURNS`, `CORS_ORIGINS`, `MAX_AUDIO_MB` added.

5. **Update `README.md`:**
   - **Performance table** — replace the `1.5s time to first audio` with the actual measured number from step 3. If the improvement is dramatic, add a "v2.1" footnote noting the Piper in-process change.
   - **Roadmap "In Progress" section** — move all four bullets to "Completed":
     ```
     - [x] Atomic LLM history commits (prevent corruption)
     - [x] In-process Piper TTS (eliminate subprocess overhead)
     - [x] Cancellable TTS tasks (interrupt mid-response)
     - [x] Security hardening (CORS, rate limiting, input validation)
     ```
   - **Installation step 3** — note that voice download is required; mention `en_GB-vctk-medium` matches the new default.
   - **Configuration section** — add a row for `MAX_AUDIO_MB`, `CORS_ORIGINS`, `MAX_HISTORY_TURNS`.

6. **Update `PERFORMANCE.md`** with the new numbers from step 3, and add a one-line note: "Piper TTS is now in-process; per-sentence cold-start has been eliminated."

7. **Write `STAGE2_PREP.md`** at repo root — a short doc handing off to Stage 2:

   ```markdown
   # Stage 2 Prep — Foundations Now in Place

   Stage 1 (critical fixes) landed. Here's what Stage 2 can build on,
   and what Stage 2 still has to design.

   ## Available primitives

   - `backend.server.Turn` — dataclass with `spawn(coro)`, `cancel()`, `wait_all()`.
     Stage 2 binds this to barge-in: when client-side VAD detects user speech,
     server calls `current_turn.cancel()` and all pending TTS stops within ~50ms.
   - `src.core.tts.TextToSpeech.synthesize_chunks(text)` — generator yielding
     int16 numpy arrays. Use this in Stage 2 to forward Piper's native chunks
     directly to the WebSocket instead of re-buffering into 8192-sample slabs.
   - `src.core.llm.LLMProcessor` — history is now safe across cancellation.
     Mid-stream cuts no longer corrupt context.

   ## Known deferred items (Stage 2 territory)

   - Sentence-boundary parser in `handle_voice_query` — current `any(p in chunk ...)`
     check is buggy but will be replaced by Stage 2's continuous overlapping TTS.
     Do not fix in isolation.
   - `src/core/assistant.py` has its own threaded streaming path that's separate
     from the WS server. Stage 2's turn manager will subsume both. CLI users
     keep current behavior until then.
   - Per-session conversation isolation: `LLMProcessor` is a module-level
     singleton; two browser tabs share history. Stage 2 design decision.

   ## Stage 2 design questions (decide before coding)

   1. Push-to-talk fallback? Continuous-listen-only is risky for laptop battery
      and privacy expectations.
   2. Show partial transcript while user is still speaking? Latency-friendly
      but user may find it distracting.
   3. VAD sensitivity defaults? Need a calibration tool, not just an env var.
   4. Echo suppression strategy: half-duplex mic gating (simple, limits barge-in
      to between TTS sentences) vs. proper AEC (complex)?
   5. On Python 3.14, `webrtcvad` has no wheel — Silero VAD (ONNX) is the
      portable choice. Note for Stage 2 dependencies.
   ```

✅ **Commit:** `docs: sync README/.env.example/PERFORMANCE; add STAGE2_PREP`

---

## Out of scope for Stage 1 (deliberate deferrals)

The following are real issues but addressed in Stage 2 or later:

- **Sentence boundary parser.** Replaced by continuous overlapping TTS in Stage 2.
- **Duplicate streaming logic between `assistant.py` and `server.py`.** Subsumed by the Stage 2 turn manager.
- **Frontend reconnect backoff.** Quality-of-life, not foundational.
- **Module-level singletons in `server.py`.** Works fine for Stage 1 + Stage 2; refactor later.
- **`assistant.py`'s old threaded `process_voice_query_streaming`.** Untouched. CLI users keep current behavior. Stage 2 may delete or rewrite.
- **Per-session conversation isolation.** Two browser tabs share `LLMProcessor.conversation_history` today. Real bug but a design change. Out of scope.
- **CI workflow, `pyproject.toml` migration, Docker.** Hygiene, not foundational.

---

## Acceptance criteria for the whole stage

The Stage 1 PR is done when **all** of the following are true:

- [ ] All 5 phases committed on `stage1-critical-fixes`.
- [ ] `pytest -v` passes; ≥12 new tests added.
- [ ] Manual smoke tests in Phase 5 all pass.
- [ ] No `subprocess` call to Piper anywhere in the codebase.
- [ ] `CORS_ORIGINS` is read from env, not hardcoded `*`.
- [ ] `PIPER_SPEAKER` setting either still works OR a warning was logged at startup explaining the fallback.
- [ ] Time-to-first-audio is measurably lower than `BASELINE.txt`. **The new number is recorded in both `BASELINE.txt` and `PERFORMANCE.md`.**
- [ ] Frontend wire format is unchanged (same message `type`s, same fields).
- [ ] Wake-word integration still works end-to-end.
- [ ] CLI (`assistant-cli`) still works — voice and text both.
- [ ] All three example scripts in `examples/` still run.
- [ ] `.env.example`, `README.md` Configuration section, and `config/settings.py` defaults all agree on every env var. No drift.
- [ ] README's "In Progress" roadmap items are moved to "Completed".
- [ ] `STAGE2_PREP.md` exists at repo root.
- [ ] PR description lists fixed bugs, commits, new tests, and the deferred follow-ups listed above.

---

## Risk register (read before merging)

| Risk | Likelihood | Mitigation in plan |
|---|---|---|
| `piper-tts` upgrade breaks user's voice selection | Medium | Speaker probe + warning + fallback in Phase 2 |
| `piper-tts>=1.3.0` not available on user's Python version | Low | Phase 2 task 2 surfaces the install error early |
| LLM atomic-commit change affects an edge case I missed | Low | Test coverage in Phase 1 includes the disconnect case |
| Turn primitive introduces a deadlock | Low | Always cancel + `wait_all` in `finally`; tested in Phase 3 |
| CORS lockdown blocks a real user setup | Medium | `CORS_ORIGINS` is configurable, documented in `.env.example` |
| Audio size cap rejects legitimate long utterances | Low | 25 MB ≈ 200s at the project's 128kbps WebM Opus; far above expected |
| Doc sync misses one of the three sources | Medium | Phase 5 acceptance criterion explicitly checks all three agree |

Anything in this register that turns out to be high-impact during implementation is a stop-the-line: pause, surface to the user, don't paper over it.