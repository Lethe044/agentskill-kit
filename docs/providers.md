# Providers

agentskill-kit talks to models over plain HTTP, so it needs no SDK. Everything runs free of charge with a local
model or a free tier. Paid keys are optional and work the same way.

Run `askit providers` to see what is ready on your machine.

| Provider | Cost | Setup |
| --- | --- | --- |
| `ollama` | free, local | Install [Ollama](https://ollama.com/download), then `ollama pull llama3.1` (or a coder model). No key needed. |
| `lmstudio` | free, local | Start the local server in LM Studio. |
| `groq` | free tier | Create a key at [console.groq.com/keys](https://console.groq.com/keys), set `GROQ_API_KEY`. |
| `gemini` | free tier | Create a key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey), set `GEMINI_API_KEY`. |
| `openrouter` | free models | Create a key at [openrouter.ai/keys](https://openrouter.ai/keys), set `OPENROUTER_API_KEY`, choose a model whose name ends in `:free`. |
| `openai` | paid, optional | Set `OPENAI_API_KEY`. |
| `anthropic` | paid, optional | Set `ANTHROPIC_API_KEY`. |
| `custom` | any | Set `ASKIT_BASE_URL`, `ASKIT_MODEL` and, if needed, `ASKIT_API_KEY`. Works with anything that speaks the OpenAI chat completions protocol (vLLM, llama.cpp server, LiteLLM, ...). |
| `mock` | free, offline | Returns a built-in example skill. For demos and tests. |

## Choosing a provider

Order of precedence: `--provider` flag, `ASKIT_PROVIDER`, `askit config set provider NAME`, then automatic detection.
Automatic detection prefers a running Ollama, then free keys (Groq, Gemini, OpenRouter), then paid keys.

```bash
askit forge --task "..." --provider groq --model llama-3.3-70b-versatile
askit config set provider ollama
```

## Models

Model names change often. Defaults are picked to work at the time of release. If a provider answers with
"model not found", list what it offers and pick one:

```bash
askit providers --models --provider groq
askit config set model <name>
```

For Ollama, the first installed model that matches a coding or general purpose family is used when you do not
choose one.

## Keys

Keep keys in environment variables or in a `.env` file next to where you run `askit`. agentskill-kit never writes keys
to its config file. `.env` is already in this repository's `.gitignore`.

## Free tier limits

Free tiers have rate limits. The client retries on HTTP 429 and 5xx responses and honours the `Retry-After`
header. If you still hit a limit, wait a minute, lower `--rounds`, or switch provider.

## Model quality

`forge` works with small local models because the loop is driven by code, not by tool calling. The quality of the
first draft depends on the model, and the checks decide whether it is good enough. A larger model usually needs
fewer rounds.

## Privacy

`forge`, `eval` and `mine --forge` send your task text, source notes and, for refinement, the generated files to the
provider you choose. Use a local model when that text is sensitive. `lint`, `scan`, `test`, `export`, `search` and
`mine` without `--forge` never contact a model.
