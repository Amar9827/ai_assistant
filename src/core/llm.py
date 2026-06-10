import logging
import ollama
import asyncio
import re
import time
from datetime import date, datetime
from groq import Groq
import httpx
import json
from typing import List, Dict, Generator
from config.settings import Settings
from src.tools.web_search import search_web, format_search_results_for_llm
from src.core.memory import get_memory_context

logger = logging.getLogger(__name__)

class LLMProcessor:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.provider = settings.LLM_PROVIDER.lower()
        self.conversation_history: List[Dict[str, str]] = []
        self.max_history_turns = getattr(settings, "MAX_HISTORY_TURNS", 20)

        # Always initialize both clients (lightweight — no model loading)
        self.ollama_client = ollama.Client(host=settings.OLLAMA_HOST)
        self.groq_client = None
        if settings.GROQ_API_KEY:
            self.groq_client = Groq(
                api_key=settings.GROQ_API_KEY,
                http_client=httpx.Client(verify=False),
            )

        # Groq rate-limit tracking: skip Groq entirely until cooldown expires
        self._groq_rate_limited_until: float = 0.0

        # Static base of JARVIS persona system prompt (date/time injected dynamically)
        self._system_prompt_base = (
            "You are J.A.R.V.I.S. — Just A Rather Very Intelligent System — "
            "a highly capable AI voice assistant inspired by the iconic AI from the Iron Man films. "
            "You serve your operator, Amar, with precision and composure.\n\n"
            "PERSONALITY:\n"
            "- Formal, composed, and precise. Professional with dry wit when appropriate.\n"
            "- Address the user as 'sir' occasionally but naturally, not robotically.\n"
            "- When you make a mistake, acknowledge it briefly and correct immediately.\n\n"
            "VOICE RULES:\n"
            "- Keep responses concise: 1-3 sentences for simple queries, up to 5 for complex ones.\n"
            "- Speak naturally as if talking, not writing. No markdown, no bullet points, no headers.\n"
            "- Never read out URLs, file paths, or code aloud.\n"
            "- Get straight to the point. No filler phrases like 'Great question!' or 'That's interesting!'.\n"
            "- Use natural spoken language: 'You have 58 gigabytes available, sir' NOT 'Available: 58GB'.\n\n"
            "KNOWLEDGE BOUNDARIES:\n"
            "{datetime_line}"
            "- Your training data ends around mid-2024. Anything after that is UNKNOWN to you.\n"
            "- For events, results, prices, or news after mid-2024: use web search or say 'I don't have that information, sir.'\n"
            "- NEVER fabricate dates, scores, names, statistics, or outcomes. If unsure, say so.\n"
            "- If asked about yourself: you are JARVIS, running locally. Do not invent capabilities you lack.\n\n"
            "SEARCH CONFLICT RULE:\n"
            "- If web search results contradict your training data, ALWAYS trust the search results.\n"
            "- They are more recent and authoritative. Never override search results with your prior beliefs.\n\n"
            "CONTEXT:\n"
            "- You are running on a Windows system (Dell Latitude 5440, i7-1370P, 32GB RAM).\n"
            "- You are a voice assistant — your responses will be spoken aloud via text-to-speech."
        )

        # Cache personal memory context (reloaded on restart, not per-query)
        self._memory_ctx = get_memory_context()

    def _get_system_prompt(self) -> dict:
        """Build the system prompt with current date and time."""
        now = datetime.now()
        datetime_line = (
            f"- Today is {now.strftime('%B %d, %Y')} and the current local time is "
            f"{now.strftime('%I:%M %p').lstrip('0')} IST.\n"
        )
        content = self._system_prompt_base.format(datetime_line=datetime_line)
        if self._memory_ctx:
            content += "\n\n" + self._memory_ctx
        return {"role": "system", "content": content}
    
    def _get_tools(self):
        """Define available tools for LLM function-calling."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web for real-time information. Use for current events, weather, news, prices, or time-sensitive queries.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query (e.g., 'weather in London', 'latest tech news', 'bitcoin price')"
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]
    
    async def _handle_tool_call(self, tool_name: str, tool_input: dict) -> str:
        """Execute a tool and return the result as a string for the LLM."""
        if tool_name == "web_search":
            query = tool_input.get("query", "")
            if not query:
                return "Error: No search query provided"
            
            logger.info(f"[TOOL] Executing web_search: {query}")
            result = await search_web(query, num_results=3, api_key=self.settings.TAVILY_API_KEY)
            formatted = format_search_results_for_llm(result)
            logger.info(f"[TOOL] Search results: {formatted[:100]}...")
            return formatted
        
        return f"Error: Unknown tool '{tool_name}'"

    @property
    def groq_rate_limited(self) -> bool:
        """True when Groq is in cooldown after a 429."""
        return time.time() < self._groq_rate_limited_until

    def _record_groq_rate_limit(self, error):
        """Parse 429 retry-after and set cooldown so we stop wasting roundtrips."""
        error_str = str(error)
        if '429' not in error_str and 'rate_limit' not in error_str:
            return
        match = re.search(r'try again in (\d+)m([\d.]+)s', error_str)
        if match:
            cooldown = int(match.group(1)) * 60 + float(match.group(2))
        else:
            cooldown = 60  # conservative default
        self._groq_rate_limited_until = time.time() + cooldown
        remaining = int(cooldown)
        logger.warning(f"[GROQ] Rate limited — skipping Groq for {remaining}s")

    @staticmethod
    def _keyword_needs_search(text: str) -> tuple[bool, str]:
        """Fast regex fallback router when Groq is unavailable. Zero tokens, <1ms."""
        text_lower = text.lower()

        # Personal questions — answered from profile, never search
        if re.search(r'\b(my name|my interest|my job|about me|my expertise|my project)\b', text_lower):
            return False, text

        # Explicit search commands — always search
        if re.search(r'\b(look it up|search for it|google it|find out|check online)\b', text_lower):
            return True, text

        # Year mentions >= 2025
        if re.search(r'\b202[5-9]\b|\b20[3-9]\d\b', text):
            return True, text

        # Trigger phrases
        triggers = [
            r'\b(who won|who will win|latest|current price|weather|forecast)\b',
            r'\b(stock price|bitcoin|crypto|score|results|standings)\b',
            r'\b(news|headline|update|announced|released|launched)\b',
            r'\b(how much does|what is the price|election)\b',
            r'\b(table|rank|ranking|playoff|finals?)\b',
            r'\bvs\.?\b',
            r'\b(new|upcoming|just came out|came out)\b',
        ]
        for pattern in triggers:
            if re.search(pattern, text_lower):
                return True, text

        return False, text

    async def classify_and_route(self, user_text: str) -> tuple[bool, str]:
        """
        Use a fast LLM call to decide whether the query needs a real-time web search,
        and rewrite it into an optimal search query incorporating conversation context.

        Returns (should_search: bool, optimized_query: str).
        Falls back to keyword router when Groq is unavailable.
        """
        if not self.groq_client or self.groq_rate_limited:
            return self._keyword_needs_search(user_text)

        # Include recent turns so follow-ups like "what about 2025?" get rewritten
        # into fully-qualified queries like "US Open tennis 2025 winner".
        recent_turns = self.conversation_history[-6:]  # last 3 user+assistant pairs
        context_block = ""
        if recent_turns:
            lines = [f"{m['role'].upper()}: {m['content'][:200]}" for m in recent_turns]
            context_block = "Recent conversation:\n" + "\n".join(lines) + "\n\n"

        prompt = (
            "You are a query router. Decide if the user's query needs a real-time web search.\n\n"
            "NO SEARCH NEEDED:\n"
            "- Greetings, thanks, goodbye, conversational chat\n"
            "- Personal questions about the USER (my name, my interests, my job, about me) — "
            "these are answered from the user profile, NOT web search\n"
            "- Personal questions about the assistant (who are you)\n"
            "- General knowledge, math, coding, definitions, history before 2024\n"
            "- Anything answerable from training data or user profile\n\n"
            "NEEDS SEARCH:\n"
            "- Questions mentioning years >= 2025, 'who won', 'what happened'\n"
            "- 'latest', 'current price', weather, stock prices, sports results, elections\n"
            "- Any factual claim about events after mid-2024\n"
            "- Explicit commands: 'look it up', 'search for it', 'google it', 'check online'\n\n"
            "QUERY REWRITING RULES:\n"
            "- The query MUST be fully self-contained — resolve ALL pronouns (it, that, they, "
            "this, he, she) using conversation history\n"
            "- Extract only the TOPIC from history, NEVER include previous answers or names "
            "that were answers to different questions\n"
            "- Example: user asked 'Who won French Open 2026?' and got 'Alexander Zverev', "
            "then asks 'Who won it in 2025?' → query='2025 French Open winner' "
            "(NOT 'Alexander Zverev 2025 French Open winner')\n"
            "- For 'look it up' commands, rewrite using the LAST USER question as the query, "
            "not the command itself\n\n"
            f"{context_block}"
            f"User query: {user_text}\n\n"
            "Reply with JSON only — no extra text:\n"
            '{"search": true or false, "query": "rewritten self-contained search query, '
            'or empty string if search is false"}'
        )

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.groq_client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                    max_tokens=80,
                    response_format={"type": "json_object"},
                ),
            )
            result = json.loads(response.choices[0].message.content)
            should_search = bool(result.get("search", False))
            query = str(result.get("query", "") or user_text).strip()
            logger.info(f"[ROUTER] search={should_search} query={query!r}")
            return should_search, query
        except Exception as e:
            logger.warning(f"[ROUTER] Classification failed ({e}), defaulting to no search")
            return False, user_text

    def initialize(self):
        """Verify primary LLM provider is reachable (fallback is best-effort)."""
        if self.provider == "groq" and self.groq_client:
            try:
                self.groq_client.models.list()
                logger.info("Groq API connected (primary)")
            except Exception as e:
                logger.warning(f"Groq API not reachable: {e} — will fall back to Ollama")
        try:
            self.ollama_client.list()
            logger.info("Ollama connected (fallback)" if self.provider == "groq" else "Ollama connected (primary)")
        except Exception as e:
            if self.provider != "groq":
                raise ConnectionError(f"Ollama not reachable: {e}")
            logger.warning(f"Ollama fallback not available: {e}")
        return True

    def generate_response(self, user_input: str, stream: bool = False):
        """
        Generate response from LLM with automatic fallback.

        If Groq is primary and fails, falls back to local Ollama.
        Returns str if stream=False, Generator[str] if stream=True.
        """
        pending_user = {"role": "user", "content": user_input}
        messages = [self._get_system_prompt()] + self.conversation_history + [pending_user]

        if self.provider == "groq" and self.groq_client and not self.groq_rate_limited:
            try:
                return self._groq_response(messages, pending_user, stream)
            except Exception as e:
                self._record_groq_rate_limit(e)
                logger.warning(f"Groq failed ({e}), falling back to Ollama")
                return self._ollama_response(messages, pending_user, stream)
        else:
            if self.groq_rate_limited:
                remaining = int(self._groq_rate_limited_until - time.time())
                logger.info(f"[GROQ] Rate limited, using Ollama directly ({remaining}s remaining)")
            return self._ollama_response(messages, pending_user, stream)

    def _groq_response(self, messages, pending_user, stream):
        """Generate response via Groq cloud API with support for function calling."""
        response = self.groq_client.chat.completions.create(
            model=self.settings.GROQ_MODEL,
            messages=messages,
            temperature=self.settings.OLLAMA_TEMPERATURE,
            stream=stream,
        )

        if stream:
            return self._stream_groq(response, pending_user)

        # Check if the LLM wants to call a tool
        choice = response.choices[0]
        if choice.message.tool_calls:
            # Handle tool calls
            return self._handle_tool_calls_sync(choice.message.tool_calls, messages, pending_user)
        
        assistant_message = choice.message.content or ""
        self.conversation_history.append(pending_user)
        self.conversation_history.append(
            {"role": "assistant", "content": assistant_message}
        )
        self._cap_history()
        return assistant_message

    def _handle_tool_calls_sync(self, tool_calls, messages, pending_user):
        """Handle tool calls synchronously (for non-streaming responses)."""
        # Build messages up to the tool call
        conversation = messages + [{"role": "assistant", "tool_calls": tool_calls}]
        
        # Execute each tool call
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
            
            # Execute the tool (need to run async code in sync context)
            try:
                result = asyncio.run(self._handle_tool_call(tool_name, tool_args))
            except Exception as e:
                result = f"Error calling tool: {str(e)}"
            
            # Add tool result to conversation
            conversation.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })
        
        # Get final response after tool calls
        final_response = self.groq_client.chat.completions.create(
            model=self.settings.GROQ_MODEL,
            messages=conversation,
            temperature=self.settings.OLLAMA_TEMPERATURE,
        )
        
        assistant_message = final_response.choices[0].message.content or ""
        self.conversation_history.append(pending_user)
        self.conversation_history.append(
            {"role": "assistant", "content": assistant_message}
        )
        self._cap_history()
        return assistant_message

    def _stream_groq(self, response, pending_user):
        """Stream chunks from Groq, committing history atomically.
        If Groq fails mid-stream before producing content, falls back to Ollama."""
        full_response = ""
        try:
            for chunk in response:
                delta = chunk.choices[0].delta
                content = delta.content if delta.content else ""
                if content:
                    full_response += content
                    yield content
        except Exception as e:
            if not full_response.strip():
                # No content produced yet — fall back to Ollama
                logger.warning(f"Groq stream failed ({e}), falling back to Ollama")
                messages = [self._get_system_prompt()] + self.conversation_history + [pending_user]
                yield from self._stream_response(
                    self.ollama_client.chat(
                        model=self.settings.OLLAMA_MODEL,
                        messages=messages,
                        options={"temperature": self.settings.OLLAMA_TEMPERATURE},
                        stream=True,
                    ),
                    pending_user,
                )
                return
            else:
                logger.warning(f"Groq stream failed mid-response ({e}), keeping partial")
        finally:
            if full_response.strip():
                self.conversation_history.append(pending_user)
                self.conversation_history.append(
                    {"role": "assistant", "content": full_response}
                )
                self._cap_history()

    def _ollama_response(self, messages, pending_user, stream):
        """Generate response via local Ollama."""
        response = self.ollama_client.chat(
            model=self.settings.OLLAMA_MODEL,
            messages=messages,
            options={"temperature": self.settings.OLLAMA_TEMPERATURE},
            stream=stream,
        )

        if stream:
            return self._stream_response(response, pending_user)

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

    def _effective_history_turns(self) -> int:
        """Fewer history turns when rate-limited to stretch the token budget."""
        if self.groq_rate_limited:
            return min(5, self.max_history_turns)
        return self.max_history_turns

    def _cap_history(self):
        """Trim conversation_history to last N turns, truncate long assistant messages."""
        max_msgs = self._effective_history_turns() * 2
        if len(self.conversation_history) > max_msgs:
            self.conversation_history = self.conversation_history[-max_msgs:]
        # Truncate long assistant messages in history to save tokens
        for msg in self.conversation_history:
            if msg["role"] == "assistant" and len(msg["content"]) > 200:
                msg["content"] = msg["content"][:200] + "..."

    def generate_streaming_sentences(self, user_input: str):
        """
        Generate response and yield complete sentences as they're ready

        This is optimized for TTS - each yielded sentence can be spoken
        while the next sentence is being generated.
        """
        return self.generate_response(user_input, stream=True)

    def reset_conversation(self):
        """Clear conversation history"""
        self.conversation_history = []
